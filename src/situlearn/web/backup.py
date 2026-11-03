"""Create rotating archives of the report database and storage."""

from __future__ import annotations

import argparse
import sqlite3
import tarfile
import tempfile
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from situlearn.web.config import Settings
from situlearn.web.objectstore import build_object_store


def _prune(backup_dir: Path, keep_days: int, *, now: float | None = None) -> None:
    if keep_days < 0:
        return
    cutoff = (time.time() if now is None else now) - keep_days * 86_400
    for archive in backup_dir.glob("situlearn-*.tar.gz"):
        if archive.stat().st_mtime < cutoff:
            archive.unlink(missing_ok=True)


def create_backup(
    data_dir: Path,
    backup_dir: Path,
    *,
    keep_days: int = 7,
    now: float | None = None,
) -> Path:
    data_dir = Path(data_dir)
    backup_dir = Path(backup_dir)
    if not data_dir.is_dir():
        raise FileNotFoundError(f"data directory not found: {data_dir}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive = backup_dir / f"situlearn-{stamp}.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        database = data_dir / "situlearn.sqlite3"
        if database.is_file():
            tar.add(database, arcname="situlearn.sqlite3")
        reports = data_dir / "reports"
        if reports.is_dir():
            tar.add(reports, arcname="reports")
    _prune(backup_dir, keep_days, now=now)
    return archive


def create_oss_backup(
    settings: Settings,
    *,
    keep_days: int = 30,
    now: float | None = None,
) -> str:
    """Upload a consistent SQLite snapshot to the configured object store."""

    database = settings.db_path
    if not database.is_file():
        raise FileNotFoundError(f"database not found: {database}")

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    prefix = f"{settings.object_prefix}backups/"
    key = f"{prefix}situlearn-{stamp}.sqlite3"
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / f"situlearn-{stamp}.sqlite3"
        source = sqlite3.connect(database)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        build_object_store(settings).put_file(key, snapshot)

    store = build_object_store(settings)
    cutoff = (time.time() if now is None else now) - keep_days * 86_400
    for existing in store.list_keys(prefix):
        name = existing.rsplit("/", 1)[-1]
        try:
            created = datetime.strptime(name, "situlearn-%Y%m%dT%H%M%SZ.sqlite3")
        except ValueError:
            continue
        if created.replace(tzinfo=UTC).timestamp() < cutoff:
            store.delete_key(existing)
    return key


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up the SituLearn data directory")
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--backup-dir", default=None)
    parser.add_argument("--keep-days", type=int, default=None)
    args = parser.parse_args(argv)

    settings = Settings.from_env()
    if args.data_dir:
        settings = replace(settings, data_dir=Path(args.data_dir))
    if args.backup_dir:
        settings = replace(settings, backup_dir=Path(args.backup_dir))
    try:
        if settings.oss_configured:
            print(
                create_oss_backup(
                    settings, keep_days=args.keep_days if args.keep_days is not None else 30
                )
            )
        else:
            print(
                create_backup(
                    settings.data_dir,
                    settings.backup_dir,
                    keep_days=args.keep_days if args.keep_days is not None else 7,
                )
            )
    except (OSError, tarfile.TarError, sqlite3.Error) as exc:
        print(f"situlearn-backup: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
