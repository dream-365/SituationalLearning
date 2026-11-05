"""SQLite metadata repository for owners, reports, and document versions."""

from __future__ import annotations

import base64
import hashlib
import re
import sqlite3
import unicodedata
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS owners (
    owner_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    token_hash TEXT UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    report_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL REFERENCES owners(owner_id),
    report_key TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('published', 'unpublished')),
    current_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT,
    unpublished_at TEXT,
    size_bytes INTEGER NOT NULL,
    document_schema_version TEXT NOT NULL,
    UNIQUE (owner_id, report_key)
);

CREATE TABLE IF NOT EXISTS report_versions (
    report_id TEXT NOT NULL REFERENCES reports(report_id) ON DELETE CASCADE,
    version TEXT NOT NULL,
    object_prefix TEXT NOT NULL DEFAULT '',
    document_sha256 TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'ready', 'superseded', 'deleted')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (report_id, version)
);

CREATE TABLE IF NOT EXISTS publish_events (
    event_id TEXT PRIMARY KEY,
    report_id TEXT,
    request_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('publish', 'unpublish')),
    result TEXT NOT NULL CHECK (result IN ('success', 'rejected', 'failed')),
    client_ip_hash TEXT NOT NULL,
    error_code TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_slug ON reports(slug);
CREATE INDEX IF NOT EXISTS idx_reports_owner_key ON reports(owner_id, report_key);
CREATE INDEX IF NOT EXISTS idx_report_versions_status ON report_versions(status, created_at);
"""

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class PublishConflict(RuntimeError):
    """A publish lost a race or targeted a stale/occupied identity."""


@dataclass(frozen=True)
class ReportRecord:
    report_id: str
    owner_id: str
    report_key: str
    slug: str
    title: str
    status: str
    current_version: str
    created_at: str
    updated_at: str
    published_at: str | None
    unpublished_at: str | None
    size_bytes: int
    document_schema_version: str


@dataclass(frozen=True)
class VersionRecord:
    report_id: str
    version: str
    object_prefix: str
    document_sha256: str
    status: str
    created_at: str


@dataclass(frozen=True)
class ReportBundle:
    report: ReportRecord
    version: VersionRecord


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def report_id_for(owner_id: str, report_key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"situlearn:{owner_id}:{report_key}"))


def _slug_prefix(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    prefix = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return prefix[:55] or "report"


def _slug_suffix(owner_id: str, report_key: str) -> str:
    digest = hashlib.sha256(f"{owner_id}:{report_key}".encode()).digest()
    encoded = base64.b32encode(digest[:8]).decode("ascii").lower().rstrip("=")
    return encoded[:8]


def make_slug(title: str, owner_id: str, report_key: str) -> str:
    return f"{_slug_prefix(title)}-{_slug_suffix(owner_id, report_key)}"


def valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.fullmatch(slug))


def _report_from_row(row: sqlite3.Row) -> ReportRecord:
    return ReportRecord(
        report_id=row["report_id"],
        owner_id=row["owner_id"],
        report_key=row["report_key"],
        slug=row["slug"],
        title=row["title"],
        status=row["status"],
        current_version=row["current_version"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        published_at=row["published_at"],
        unpublished_at=row["unpublished_at"],
        size_bytes=row["size_bytes"],
        document_schema_version=row["document_schema_version"],
    )


def _version_from_row(row: sqlite3.Row) -> VersionRecord:
    return VersionRecord(
        report_id=row["report_id"],
        version=row["version"],
        object_prefix=row["object_prefix"],
        document_sha256=row["document_sha256"],
        status=row["status"],
        created_at=row["created_at"],
    )


class ReportRepository:
    """All report metadata writes go through a single-writer SQLite database."""

    def __init__(self, db_path: Path, *, busy_timeout_ms: int = 5_000) -> None:
        self.db_path = db_path
        self.busy_timeout_ms = busy_timeout_ms

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self.db_path,
            timeout=self.busy_timeout_ms / 1_000,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    def initialize(
        self,
        *,
        bootstrap_owner_id: str = "owner-0001",
        bootstrap_name: str = "default",
        bootstrap_token_hash: str | None = None,
    ) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA foreign_keys = OFF")
            try:
                self._migrate_legacy(connection, bootstrap_owner_id)
                connection.executescript(_SCHEMA)
                self._seed_owner(
                    connection,
                    bootstrap_owner_id,
                    bootstrap_name,
                    bootstrap_token_hash,
                )
            finally:
                connection.execute("PRAGMA foreign_keys = ON")

    def seed_owner(
        self, owner_id: str, name: str, token_hash: str | None = None
    ) -> None:
        with self._connection() as connection:
            self._seed_owner(connection, owner_id, name, token_hash)

    @staticmethod
    def _seed_owner(
        connection: sqlite3.Connection,
        owner_id: str,
        name: str,
        token_hash: str | None,
    ) -> None:
        connection.execute(
            """
            INSERT INTO owners (owner_id, name, token_hash, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(owner_id) DO NOTHING
            """,
            (owner_id, name, token_hash, _now()),
        )

    @staticmethod
    def _migrate_legacy(connection: sqlite3.Connection, bootstrap_owner_id: str) -> None:
        """Upgrade the pre-owner schema in place, preserving old slugs."""

        reports = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
        ).fetchone()
        if reports is None:
            return
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(reports)")
        }
        if "owner_id" in columns:
            return

        connection.executescript(
            """
            CREATE TABLE owners (
                owner_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                token_hash TEXT UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE reports_owner_migrated (
                report_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL REFERENCES owners(owner_id),
                report_key TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('published', 'unpublished')),
                current_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT,
                unpublished_at TEXT,
                size_bytes INTEGER NOT NULL,
                document_schema_version TEXT NOT NULL,
                UNIQUE (owner_id, report_key)
            );

            CREATE TABLE report_versions_owner_migrated (
                report_id TEXT NOT NULL REFERENCES reports_owner_migrated(report_id)
                    ON DELETE CASCADE,
                version TEXT NOT NULL,
                object_prefix TEXT NOT NULL DEFAULT '',
                document_sha256 TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('pending', 'ready', 'superseded', 'deleted')
                ),
                created_at TEXT NOT NULL,
                PRIMARY KEY (report_id, version)
            );
            """
        )
        connection.execute(
            "INSERT INTO owners (owner_id, name, token_hash, created_at) VALUES (?, ?, NULL, ?)",
            (bootstrap_owner_id, "default", _now()),
        )
        connection.execute(
            """
            INSERT INTO reports_owner_migrated (
                report_id, owner_id, report_key, slug, title, status,
                current_version, created_at, updated_at, published_at,
                unpublished_at, size_bytes, document_schema_version
            )
            SELECT report_id, ?, report_key, slug, title, status,
                   current_version, created_at, updated_at, published_at,
                   unpublished_at, size_bytes, manifest_schema_version
              FROM reports
            """,
            (bootstrap_owner_id,),
        )
        connection.execute(
            """
            INSERT INTO report_versions_owner_migrated (
                report_id, version, object_prefix, document_sha256, status, created_at
            )
            SELECT report_id, version, object_prefix, manifest_sha256,
                   CASE status WHEN 'active' THEN 'ready' ELSE status END,
                   created_at
              FROM report_versions
            """
        )
        connection.execute("DROP TABLE report_versions")
        connection.execute("DROP TABLE reports")
        connection.execute("ALTER TABLE reports_owner_migrated RENAME TO reports")
        connection.execute(
            "ALTER TABLE report_versions_owner_migrated RENAME TO report_versions"
        )

    def get_by_key(self, owner_id: str, report_key: str) -> ReportRecord | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE owner_id = ? AND report_key = ?",
                (owner_id, report_key),
            ).fetchone()
        return _report_from_row(row) if row else None

    def get_by_slug(
        self, owner_id: str, slug: str, *, include_unpublished: bool = False
    ) -> ReportRecord | None:
        query = "SELECT * FROM reports WHERE owner_id = ? AND slug = ?"
        if not include_unpublished:
            query += " AND status = 'published'"
        with self._connection() as connection:
            row = connection.execute(query, (owner_id, slug)).fetchone()
        return _report_from_row(row) if row else None

    def get_current_bundle(
        self, slug: str, *, include_unpublished: bool = False
    ) -> ReportBundle | None:
        query = """
            SELECT r.*, v.version AS version, v.object_prefix AS object_prefix,
                   v.document_sha256 AS document_sha256,
                   v.status AS version_status, v.created_at AS version_created_at
            FROM reports r
            JOIN report_versions v
              ON v.report_id = r.report_id AND v.version = r.current_version
            WHERE r.slug = ?
        """
        if not include_unpublished:
            query += " AND r.status = 'published'"
        with self._connection() as connection:
            row = connection.execute(query, (slug,)).fetchone()
        if not row:
            return None
        version = VersionRecord(
            report_id=row["report_id"],
            version=row["version"],
            object_prefix=row["object_prefix"],
            document_sha256=row["document_sha256"],
            status=row["version_status"],
            created_at=row["version_created_at"],
        )
        return ReportBundle(report=_report_from_row(row), version=version)

    def list_reports(self, owner_id: str) -> list[ReportRecord]:
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM reports WHERE owner_id = ? ORDER BY created_at",
                (owner_id,),
            ).fetchall()
        return [_report_from_row(row) for row in rows]

    def count_owner_reports(self, owner_id: str) -> int:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM reports WHERE owner_id = ?", (owner_id,)
            ).fetchone()
        return int(row[0])

    def list_current_bundles(self) -> list[ReportBundle]:
        query = """
            SELECT r.*, v.version AS version, v.object_prefix AS object_prefix,
                   v.document_sha256 AS document_sha256,
                   v.status AS version_status, v.created_at AS version_created_at
            FROM reports r
            JOIN report_versions v
              ON v.report_id = r.report_id AND v.version = r.current_version
            ORDER BY r.created_at
        """
        with self._connection() as connection:
            rows = connection.execute(query).fetchall()
        bundles: list[ReportBundle] = []
        for row in rows:
            version = VersionRecord(
                report_id=row["report_id"],
                version=row["version"],
                object_prefix=row["object_prefix"],
                document_sha256=row["document_sha256"],
                status=row["version_status"],
                created_at=row["version_created_at"],
            )
            bundles.append(
                ReportBundle(report=_report_from_row(row), version=version)
            )
        return bundles

    def finish_publish(
        self,
        *,
        owner_id: str,
        report_key: str,
        title: str,
        version: str,
        object_prefix: str,
        document_sha256: str,
        size_bytes: int,
        schema_version: str,
        expected_current_version: str | None,
        requested_slug: str | None,
        request_id: str,
        client_ip_hash: str,
    ) -> ReportRecord:
        if requested_slug is not None and not valid_slug(requested_slug):
            raise PublishConflict("requested slug is invalid")
        now = _now()
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT * FROM reports WHERE owner_id = ? AND report_key = ?",
                (owner_id, report_key),
            ).fetchone()
            if existing:
                if existing["current_version"] != expected_current_version:
                    raise PublishConflict("report was published concurrently")
                if requested_slug is not None and requested_slug != existing["slug"]:
                    raise PublishConflict("an existing report cannot change its slug")
                report_id = existing["report_id"]
                slug = existing["slug"]
                created_at = existing["created_at"]
                published_at = existing["published_at"] or now
                connection.execute(
                    """
                    UPDATE reports
                       SET title = ?, status = 'published', current_version = ?,
                           updated_at = ?, published_at = ?, unpublished_at = NULL,
                           size_bytes = ?, document_schema_version = ?
                     WHERE report_id = ?
                    """,
                    (
                        title,
                        version,
                        now,
                        published_at,
                        size_bytes,
                        schema_version,
                        report_id,
                    ),
                )
                connection.execute(
                    """
                    UPDATE report_versions
                       SET status = 'superseded'
                     WHERE report_id = ? AND version != ? AND status = 'ready'
                    """,
                    (report_id, version),
                )
            else:
                if expected_current_version is not None:
                    raise PublishConflict("report does not exist at the expected version")
                report_id = report_id_for(owner_id, report_key)
                slug = requested_slug or make_slug(title, owner_id, report_key)
                occupied = connection.execute(
                    "SELECT report_id FROM reports WHERE slug = ?", (slug,)
                ).fetchone()
                if occupied is not None:
                    raise PublishConflict("requested slug is already in use")
                created_at = now
                published_at = now
                try:
                    connection.execute(
                        """
                        INSERT INTO reports (
                            report_id, owner_id, report_key, slug, title, status,
                            current_version, created_at, updated_at, published_at,
                            unpublished_at, size_bytes, document_schema_version
                        ) VALUES (?, ?, ?, ?, ?, 'published', ?, ?, ?, ?, NULL, ?, ?)
                        """,
                        (
                            report_id,
                            owner_id,
                            report_key,
                            slug,
                            title,
                            version,
                            created_at,
                            now,
                            published_at,
                            size_bytes,
                            schema_version,
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise PublishConflict("report identity already exists") from exc

            try:
                connection.execute(
                    """
                    INSERT INTO report_versions (
                        report_id, version, object_prefix, document_sha256,
                        status, created_at
                    ) VALUES (?, ?, ?, ?, 'ready', ?)
                    """,
                    (report_id, version, object_prefix, document_sha256, now),
                )
            except sqlite3.IntegrityError as exc:
                raise PublishConflict(f"version already exists: {version}") from exc

            self._insert_event(
                connection,
                report_id=report_id,
                request_id=request_id,
                action="publish",
                result="success",
                client_ip_hash=client_ip_hash,
                error_code=None,
                created_at=now,
            )
            row = connection.execute(
                "SELECT * FROM reports WHERE report_id = ?", (report_id,)
            ).fetchone()
        if row is None:  # pragma: no cover
            raise RuntimeError("published report disappeared")
        return _report_from_row(row)

    def unpublish(
        self, owner_id: str, slug: str, *, request_id: str, client_ip_hash: str
    ) -> ReportRecord | None:
        now = _now()
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT * FROM reports WHERE owner_id = ? AND slug = ?",
                (owner_id, slug),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                """
                UPDATE reports
                   SET status = 'unpublished', updated_at = ?, unpublished_at = ?
                 WHERE report_id = ?
                """,
                (now, now, row["report_id"]),
            )
            self._insert_event(
                connection,
                report_id=row["report_id"],
                request_id=request_id,
                action="unpublish",
                result="success",
                client_ip_hash=client_ip_hash,
                error_code=None,
                created_at=now,
            )
            updated = connection.execute(
                "SELECT * FROM reports WHERE report_id = ?", (row["report_id"],)
            ).fetchone()
        return _report_from_row(updated) if updated else None

    def record_event(
        self,
        *,
        report_id: str | None,
        request_id: str,
        action: str,
        result: str,
        client_ip_hash: str,
        error_code: str | None,
    ) -> None:
        with self._connection() as connection:
            self._insert_event(
                connection,
                report_id=report_id,
                request_id=request_id,
                action=action,
                result=result,
                client_ip_hash=client_ip_hash,
                error_code=error_code,
                created_at=_now(),
            )
            connection.commit()

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        *,
        report_id: str | None,
        request_id: str,
        action: str,
        result: str,
        client_ip_hash: str,
        error_code: str | None,
        created_at: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO publish_events (
                event_id, report_id, request_id, action, result,
                client_ip_hash, error_code, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex,
                report_id,
                request_id,
                action,
                result,
                client_ip_hash,
                error_code,
                created_at,
            ),
        )

    def expired_versions(self, ttl_hours: int) -> list[VersionRecord]:
        cutoff = datetime.now(UTC) - timedelta(hours=ttl_hours)
        cutoff_text = cutoff.isoformat(timespec="seconds").replace("+00:00", "Z")
        with self._connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM report_versions
                 WHERE status = 'superseded' AND created_at < ?
                 ORDER BY created_at
                """,
                (cutoff_text,),
            ).fetchall()
        return [_version_from_row(row) for row in rows]

    def mark_version_deleted(self, report_id: str, version: str) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                UPDATE report_versions SET status = 'deleted'
                 WHERE report_id = ? AND version = ?
                """,
                (report_id, version),
            )
            connection.commit()

    def stats(self) -> tuple[int, int]:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(size_bytes), 0)
                  FROM reports
                 WHERE status = 'published'
                """
            ).fetchone()
        return int(row[0]), int(row[1])


__all__ = [
    "PublishConflict",
    "ReportBundle",
    "ReportRecord",
    "ReportRepository",
    "VersionRecord",
    "make_slug",
    "report_id_for",
    "valid_slug",
]
