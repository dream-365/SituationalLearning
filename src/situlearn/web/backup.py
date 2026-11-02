"""Create rotating archives of the report database and storage."""

from __future__ import annotations

import argparse
import tarfile
import time
from datetime import UTC, datetime
from pathlib import Path


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up the SituLearn data directory")
    parser.add_argument("--data-dir", default="/data")
    parser.add_argument("--backup-dir", default="/backup")
    parser.add_argument("--keep-days", type=int, default=7)
    args = parser.parse_args(argv)
    try:
        archive = create_backup(
            Path(args.data_dir),
            Path(args.backup_dir),
            keep_days=args.keep_days,
        )
    except (OSError, tarfile.TarError) as exc:
        print(f"situlearn-backup: {exc}")
        return 1
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
