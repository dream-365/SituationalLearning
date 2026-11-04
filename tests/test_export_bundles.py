"""Tests for exporting legacy manifest bundles from object storage."""

from __future__ import annotations

import json
from pathlib import Path

from web_fixtures import settings

from situlearn.web.export_bundles import export_old_bundles
from situlearn.web.repository import ReportRepository, report_id_for
from situlearn.web.storage import ReportStore


def test_export_old_bundles(tmp_path: Path) -> None:
    config = settings(tmp_path)
    repository = ReportRepository(config.db_path)
    repository.initialize(bootstrap_owner_id=config.default_owner_id)
    store = ReportStore(config)

    owner_id = config.default_owner_id
    report_key = "b" * 64
    report_id = report_id_for(owner_id, report_key)
    prefix = f"reports/{report_id}/versions/v1/"
    repository.finish_publish(
        owner_id=owner_id,
        report_key=report_key,
        title="Legacy Report",
        version="v1",
        object_prefix=prefix,
        document_sha256="0" * 64,
        size_bytes=100,
        schema_version="1.0.0",
        expected_current_version=None,
        requested_slug="legacy-report",
        request_id="req",
        client_ip_hash="ip",
    )
    store.objects.put_bytes(
        f"{prefix}manifest.json",
        json.dumps({"schema_version": "1.0.0", "narrative": {"title": "Legacy Report"}}).encode(),
    )
    store.objects.put_bytes(f"{prefix}assets/audio/a.mp3", b"audio")

    exported, skipped = export_old_bundles(store, repository, tmp_path / "export")

    assert (exported, skipped) == (1, 0)
    root = tmp_path / "export" / report_key
    assert (root / "manifest.json").is_file()
    assert (root / "assets" / "audio" / "a.mp3").read_bytes() == b"audio"
    assert json.loads((root / "bundle.json").read_text(encoding="utf-8"))["slug"] == "legacy-report"
