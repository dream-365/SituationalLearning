"""Immutable document storage and .situ upload validation."""

from __future__ import annotations

import contextlib
import hashlib
import json
import re
import shutil
import threading
import time
import unicodedata
import uuid
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from situlearn.document import (
    Document,
    DocumentValidationError,
    parse_document,
    raise_for_errors,
)
from situlearn.web.config import Settings
from situlearn.web.objectstore import (
    ObjectNotFound,
    ObjectStore,
    build_object_store,
)

_SHARED_WITH_MACOS = {".DS_Store"}


def _ignored_member(path: PurePosixPath) -> bool:
    name = path.name
    return (
        name in _SHARED_WITH_MACOS
        or name.startswith("._")
        or path.parts[:1] == ("__MACOSX",)
    )


class PublishValidationError(ValueError):
    """A publish archive failed validation before it could be installed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StagedReport:
    upload_id: str
    root: Path
    owner_id: str
    report_key: str
    title: str
    document: Document
    canonical_bytes: bytes
    public_bytes: bytes
    schema_version: str
    size_bytes: int
    document_sha256: str


@dataclass(frozen=True)
class VersionRef:
    report_id: str
    version: str
    object_prefix: str


def _safe_member_path(name: str) -> PurePosixPath:
    if not name or name.startswith("/") or "\\" in name or "\x00" in name:
        raise PublishValidationError(
            "ERR_PUBLISH_INVALID_ARCHIVE", f"unsafe archive path: {name!r}"
        )
    if "//" in name or unicodedata.normalize("NFC", name) != name:
        raise PublishValidationError(
            "ERR_PUBLISH_INVALID_ARCHIVE", f"unsafe archive path: {name!r}"
        )
    path = PurePosixPath(name)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise PublishValidationError(
            "ERR_PUBLISH_INVALID_ARCHIVE", f"unsafe archive path: {name!r}"
        )
    return path


def _check_zip_members(
    infos: list[zipfile.ZipInfo], settings: Settings
) -> dict[str, zipfile.ZipInfo]:
    files: dict[str, zipfile.ZipInfo] = {}
    folded: set[str] = set()
    total_size = 0
    for info in infos:
        path = _safe_member_path(info.filename)
        if _ignored_member(path):
            continue
        if info.is_dir():
            continue
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise PublishValidationError(
                "ERR_PUBLISH_INVALID_ARCHIVE", f"symlink entry: {info.filename!r}"
            )
        key = str(path)
        if key in files:
            raise PublishValidationError(
                "ERR_PUBLISH_INVALID_ARCHIVE", f"duplicate archive path: {key!r}"
            )
        if key.casefold() in folded:
            raise PublishValidationError(
                "ERR_PUBLISH_INVALID_ARCHIVE",
                f"case-colliding archive path: {key!r}",
            )
        folded.add(key.casefold())
        if key != "document.json" and not key.startswith("media/"):
            raise PublishValidationError(
                "ERR_PUBLISH_INVALID_ARCHIVE",
                f"unexpected archive entry: {key!r}",
            )
        files[key] = info
        total_size += info.file_size
        if len(files) > settings.max_report_files:
            raise PublishValidationError(
                "ERR_PUBLISH_PAYLOAD_TOO_LARGE",
                f"archive contains more than {settings.max_report_files} files",
            )
        if total_size > settings.max_report_bytes:
            raise PublishValidationError(
                "ERR_PUBLISH_PAYLOAD_TOO_LARGE",
                f"archive exceeds {settings.max_report_bytes} bytes",
            )
    if "document.json" not in files:
        raise PublishValidationError(
            "ERR_PUBLISH_INVALID_DOCUMENT", "document.json is missing from archive root"
        )
    return files


def _extract_members(
    archive: zipfile.ZipFile,
    members: dict[str, zipfile.ZipInfo],
    destination: Path,
) -> None:
    for name in sorted(members):
        target = destination.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(members[name]) as source, target.open("wb") as handle:
            shutil.copyfileobj(source, handle)


def _public_projection(document: Document) -> bytes:
    payload = document.model_dump(mode="json", exclude_none=True)
    meta = payload.get("meta")
    if isinstance(meta, dict):
        meta.pop("id", None)
        source = meta.get("source")
        if isinstance(source, dict):
            source.pop("filename", None)
            source.pop("sha256", None)
            if not source:
                meta.pop("source", None)
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _report_key(document: Document) -> str:
    source_sha = document.meta.source.sha256 if document.meta.source else None
    key = source_sha or document.meta.id
    if not key or not re.fullmatch(r"[0-9a-f]{64}", key):
        raise PublishValidationError(
            "ERR_PUBLISH_INVALID_DOCUMENT",
            "document needs meta.source.sha256 or meta.id as 64 lowercase hex",
        )
    return key


class ReportStore:
    """Stage uploads, validate documents, then install immutable objects."""

    def __init__(
        self, settings: Settings, object_store: ObjectStore | None = None
    ) -> None:
        self.settings = settings
        self.objects = object_store or build_object_store(settings)
        self._document_cache: dict[str, tuple[float, bytes]] = {}
        self._cache_lock = threading.Lock()

    def _version_prefix(self, owner_id: str, report_id: str, version: str) -> str:
        return (
            f"{self.settings.object_prefix}owners/{owner_id}/reports/"
            f"{report_id}/{version}/"
        )

    def stage(self, archive_path: Path, *, owner_id: str) -> StagedReport:
        self.settings.ensure_directories()
        upload_id = uuid.uuid4().hex
        staging_root = self.settings.staging_dir / upload_id
        staging_root.mkdir(parents=True, exist_ok=False)
        try:
            try:
                with zipfile.ZipFile(archive_path) as archive:
                    members = _check_zip_members(archive.infolist(), self.settings)
                    _extract_members(archive, members, staging_root)
            except (zipfile.BadZipFile, OSError) as exc:
                raise PublishValidationError(
                    "ERR_PUBLISH_INVALID_ARCHIVE", f"cannot read archive: {exc}"
                ) from exc

            document_path = staging_root / "document.json"
            canonical_bytes = document_path.read_bytes()
            try:
                document, issues = parse_document(canonical_bytes, mode="write")
                raise_for_errors(issues)
            except DocumentValidationError as exc:
                raise PublishValidationError(
                    "ERR_PUBLISH_INVALID_DOCUMENT", str(exc)
                ) from exc
            except ValueError as exc:
                raise PublishValidationError(
                    "ERR_PUBLISH_INVALID_DOCUMENT", f"invalid document: {exc}"
                ) from exc

            for resource in document.resources.values():
                path = staging_root.joinpath(*PurePosixPath(resource.href).parts)
                if not path.is_file():
                    raise PublishValidationError(
                        "ERR_PUBLISH_ASSET_MISSING",
                        f"referenced resource is missing: {resource.href}",
                    )
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != resource.sha256:
                    raise PublishValidationError(
                        "ERR_PUBLISH_HASH_MISMATCH",
                        f"resource hash mismatch: {resource.href}",
                    )

            public_bytes = _public_projection(document)
            size_bytes = sum(
                path.stat().st_size for path in staging_root.rglob("*") if path.is_file()
            )
            return StagedReport(
                upload_id=upload_id,
                root=staging_root,
                owner_id=owner_id,
                report_key=_report_key(document),
                title=document.meta.title,
                document=document,
                canonical_bytes=canonical_bytes,
                public_bytes=public_bytes,
                schema_version="1",
                size_bytes=size_bytes,
                document_sha256=hashlib.sha256(canonical_bytes).hexdigest(),
            )
        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise

    def install(
        self, staged: StagedReport, *, report_id: str, version: str
    ) -> VersionRef:
        prefix = self._version_prefix(staged.owner_id, report_id, version)
        if next(self.objects.list_keys(prefix), None) is not None:
            raise PublishValidationError(
                "ERR_PUBLISH_CONFLICT", f"version already exists: {version}"
            )
        try:
            self.objects.put_bytes(f"{prefix}canonical.json", staged.canonical_bytes)
            self.objects.put_bytes(f"{prefix}document.json", staged.public_bytes)
            for resource in staged.document.resources.values():
                source = staged.root.joinpath(*PurePosixPath(resource.href).parts)
                self.objects.put_file(f"{prefix}{resource.href}", source)
        except Exception:
            with contextlib.suppress(Exception):
                self.objects.delete_prefix(prefix)
            raise
        shutil.rmtree(staged.root, ignore_errors=True)
        return VersionRef(report_id=report_id, version=version, object_prefix=prefix)

    def abort(self, staged: StagedReport) -> None:
        shutil.rmtree(staged.root, ignore_errors=True)

    def remove_prefix(self, object_prefix: str) -> None:
        self.objects.delete_prefix(object_prefix)
        with self._cache_lock:
            self._document_cache.pop(object_prefix, None)

    def remove_version(self, report_id: str, version: str) -> None:
        with self._cache_lock:
            for key in list(self._document_cache):
                if f"/{report_id}/{version}/" in key:
                    self._document_cache.pop(key, None)

    def read_document(self, object_prefix: str) -> bytes:
        if not object_prefix:
            raise ObjectNotFound("version has no object prefix")
        now = time.monotonic()
        with self._cache_lock:
            cached = self._document_cache.get(object_prefix)
        if cached is not None and now - cached[0] < self.settings.oss_read_cache_ttl_s:
            return cached[1]
        data = self.objects.get_bytes(f"{object_prefix}document.json")
        with self._cache_lock:
            self._document_cache[object_prefix] = (now, data)
        return data

    def read_canonical(self, object_prefix: str) -> bytes:
        return self.objects.get_bytes(f"{object_prefix}canonical.json")

    def asset_size(self, object_prefix: str, asset_path: str) -> int:
        return self.objects.stat(f"{object_prefix}{asset_path}")

    def read_asset_range(
        self, object_prefix: str, asset_path: str, start: int, end: int
    ) -> Iterator[bytes]:
        return self.objects.read_range(f"{object_prefix}{asset_path}", start, end)

    def healthcheck(self) -> None:
        self.objects.healthcheck()


__all__ = [
    "PublishValidationError",
    "ReportStore",
    "StagedReport",
    "VersionRef",
]
