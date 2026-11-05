"""Export legacy manifest bundles from the object store for migration."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from situlearn.web.config import Settings
from situlearn.web.objectstore import ObjectNotFound
from situlearn.web.repository import ReportRepository
from situlearn.web.storage import ReportStore


def export_old_bundles(
    store: ReportStore,
    repository: ReportRepository,
    out_root: Path,
) -> tuple[int, int]:
    """Write old bundles as ``<out>/<report_key>/manifest.json + assets/``."""

    out_root.mkdir(parents=True, exist_ok=True)
    exported = 0
    skipped = 0
    for bundle in repository.list_current_bundles():
        prefix = bundle.version.object_prefix
        if not prefix:
            skipped += 1
            continue
        try:
            manifest = store.objects.get_bytes(f"{prefix}manifest.json")
        except ObjectNotFound:
            skipped += 1
            continue
        root = out_root / bundle.report.report_key
        root.mkdir(parents=True, exist_ok=True)
        (root / "manifest.json").write_bytes(manifest)
        for key in store.objects.list_keys(prefix):
            relative = key[len(prefix) :]
            if relative == "manifest.json" or not relative.startswith("assets/"):
                continue
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(store.objects.get_bytes(key))
        (root / "bundle.json").write_text(
            json.dumps(
                {
                    "slug": bundle.report.slug,
                    "published_at": bundle.report.published_at,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        exported += 1
    return exported, skipped


def export_from_settings(
    settings: Settings, out_root: Path
) -> tuple[int, int]:
    repository = ReportRepository(
        settings.db_path, busy_timeout_ms=settings.db_busy_timeout_ms
    )
    repository.initialize(
        bootstrap_owner_id=settings.default_owner_id,
        bootstrap_name=settings.owner_name,
    )
    store = ReportStore(settings)
    return export_old_bundles(store, repository, out_root)


def settings_with_data_dir(data_dir: Path) -> Settings:
    settings = Settings.from_env()
    return dataclasses.replace(
        settings,
        data_dir=data_dir,
        _staging_dir=data_dir / "staging",
    )


__all__ = [
    "export_from_settings",
    "export_old_bundles",
    "settings_with_data_dir",
]
