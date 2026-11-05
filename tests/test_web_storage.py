"""Tests for document-based upload staging and immutable storage."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from web_fixtures import document, media, settings, situ_bytes

from situlearn.web.config import Settings
from situlearn.web.storage import PublishValidationError, ReportStore


def _archive(
    tmp_path: Path,
    *,
    document_dict: dict | None = None,
    files: dict[str, bytes] | None = None,
    name: str = "report.situ",
) -> Path:
    path = tmp_path / name
    path.write_bytes(situ_bytes(document_dict, files))
    return path


def _error_code(call) -> str:
    with pytest.raises(PublishValidationError) as captured:
        call()
    return captured.value.code


def test_stage_and_install_document(tmp_path: Path) -> None:
    store = ReportStore(settings(tmp_path))
    staged = store.stage(_archive(tmp_path), owner_id="owner-0001")

    assert staged.report_key == "a" * 64
    assert staged.title == "Web Test Report"
    assert staged.owner_id == "owner-0001"
    public = json.loads(staged.public_bytes)
    assert "id" not in public["meta"]
    assert "sha256" not in public["meta"]["source"]
    assert "filename" not in public["meta"]["source"]
    assert json.loads(staged.canonical_bytes)["meta"]["id"] == "a" * 64

    ref = store.install(staged, report_id="report-1", version="v1")
    assert ref.object_prefix.endswith("owners/owner-0001/reports/report-1/v1/")
    assert json.loads(store.read_document(ref.object_prefix))["meta"]["title"] == "Web Test Report"
    assert json.loads(store.read_canonical(ref.object_prefix))["meta"]["id"] == "a" * 64
    assert store.asset_size(ref.object_prefix, "media/audio/s0.mp3") == len(media()["media/audio/s0.mp3"])


def test_stage_rejects_invalid_document(tmp_path: Path) -> None:
    store = ReportStore(settings(tmp_path))
    assert _error_code(
        lambda: store.stage(_archive(tmp_path, document_dict={}), owner_id="owner-0001")
    ) == "ERR_PUBLISH_INVALID_DOCUMENT"


def test_stage_rejects_extra_entry(tmp_path: Path) -> None:
    store = ReportStore(settings(tmp_path))
    files = media()
    files["index.html"] = b"x"
    assert _error_code(
        lambda: store.stage(_archive(tmp_path, files=files), owner_id="owner-0001")
    ) == "ERR_PUBLISH_INVALID_ARCHIVE"


def test_stage_rejects_path_traversal(tmp_path: Path) -> None:
    store = ReportStore(settings(tmp_path))
    path = tmp_path / "bad.situ"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("document.json", json.dumps(document()).encode())
        archive.writestr("../evil", b"x")
    assert _error_code(
        lambda: store.stage(path, owner_id="owner-0001")
    ) == "ERR_PUBLISH_INVALID_ARCHIVE"


def test_stage_rejects_symlink(tmp_path: Path) -> None:
    store = ReportStore(settings(tmp_path))
    path = tmp_path / "symlink.situ"
    info = zipfile.ZipInfo("media/link")
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("document.json", json.dumps(document()).encode())
        archive.writestr(info, "target")
    assert _error_code(
        lambda: store.stage(path, owner_id="owner-0001")
    ) == "ERR_PUBLISH_INVALID_ARCHIVE"


def test_stage_rejects_missing_asset(tmp_path: Path) -> None:
    store = ReportStore(settings(tmp_path))
    files = media()
    del files["media/audio/s0.mp3"]
    assert _error_code(
        lambda: store.stage(_archive(tmp_path, files=files), owner_id="owner-0001")
    ) == "ERR_PUBLISH_ASSET_MISSING"


def test_stage_rejects_hash_mismatch(tmp_path: Path) -> None:
    store = ReportStore(settings(tmp_path))
    files = media()
    files["media/audio/s0.mp3"] = b"tampered"
    assert _error_code(
        lambda: store.stage(_archive(tmp_path, files=files), owner_id="owner-0001")
    ) == "ERR_PUBLISH_HASH_MISMATCH"


def test_stage_rejects_oversized_payload(tmp_path: Path) -> None:
    store = ReportStore(
        Settings(
            data_dir=tmp_path / "data",
            backup_dir=tmp_path / "backup",
            max_report_bytes=100,
        )
    )
    path = _archive(tmp_path)
    assert _error_code(
        lambda: store.stage(path, owner_id="owner-0001")
    ) == "ERR_PUBLISH_PAYLOAD_TOO_LARGE"
