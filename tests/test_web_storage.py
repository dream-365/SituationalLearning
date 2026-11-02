"""Tests for immutable report storage and atomic metadata switches."""

from __future__ import annotations

import io
import json
import tarfile
import uuid
from pathlib import Path

import pytest

from situlearn.web.config import Settings
from situlearn.web.repository import (
    PublishConflict,
    ReportRepository,
    report_id_for,
)
from situlearn.web.storage import PublishValidationError, ReportStore

REPORT_KEY = "a" * 64


def _manifest(report_key: str = REPORT_KEY, title: str = "Test Report") -> dict:
    return {
        "schema_version": "1.0.0",
        "source": {
            "filename": "sample.srt",
            "sha256": report_key,
            "duration_ms": 1_000,
            "cue_count": 1,
        },
        "config": {},
        "narrative": {
            "title": title,
            "logline": "A test logline",
            "background": "A test background",
            "sections": [
                {
                    "section_id": "s1",
                    "heading": "Heading",
                    "start_ms": 0,
                    "end_ms": 1_000,
                    "summary": "Summary",
                    "key_terms": [],
                    "spoken_text": "Spoken text",
                    "audio_refs": ["assets/audio/section.mp3"],
                    "audio_status": "ready",
                }
            ],
        },
        "terms": [
            {
                "term": "word",
                "ipa": "/w/",
                "part_of_speech": "noun",
                "definition_zh": "中文释义内容",
                "definition_en": "English definition",
                "context_sentence": "A context sentence.",
                "why_it_matters": "It matters for the argument.",
                "section_id": "s1",
                "category": "domain_term",
                "audio_ref": "assets/audio/term.mp3",
                "audio_source": "dictionary",
                "sources": [{"name": "source", "url": "https://example.com"}],
            }
        ],
        "assets": [
            {
                "asset_id": "a1",
                "path": "assets/audio/section.mp3",
                "duration_ms": 1_000,
                "text_sha256": "b" * 64,
                "source": "tts",
            }
        ],
        "warnings": [],
    }


def _archive(
    tmp_path: Path,
    *,
    manifest: dict | None = None,
    omit: set[str] | None = None,
) -> Path:
    source = tmp_path / f"source-{uuid.uuid4().hex}"
    (source / "assets" / "audio").mkdir(parents=True)
    (source / "manifest.json").write_text(
        json.dumps(manifest or _manifest(), ensure_ascii=False), encoding="utf-8"
    )
    (source / "assets" / "audio" / "section.mp3").write_bytes(b"section-audio")
    (source / "assets" / "audio" / "term.mp3").write_bytes(b"term-audio")
    for relative in omit or set():
        (source / relative).unlink(missing_ok=True)
    archive = tmp_path / "report.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for path in sorted(source.rglob("*")):
            tar.add(
                path,
                arcname=str(path.relative_to(source)),
                recursive=False,
            )
    return archive


def _settings(tmp_path: Path, **overrides) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backup",
        **overrides,
    )


def _error_code(action) -> str:
    with pytest.raises(PublishValidationError) as captured:
        action()
    return captured.value.code


def test_stage_valid_archive_reads_manifest(tmp_path):
    store = ReportStore(_settings(tmp_path))

    staged = store.stage(_archive(tmp_path), report_key=REPORT_KEY)

    assert staged.title == "Test Report"
    assert staged.schema_version == "1.0.0"
    assert staged.size_bytes > 0
    assert staged.manifest_sha256
    assert (staged.root / "manifest.json").is_file()


def test_install_and_first_publish(tmp_path):
    settings = _settings(tmp_path)
    store = ReportStore(settings)
    repository = ReportRepository(settings.db_path)
    repository.initialize()

    staged = store.stage(_archive(tmp_path), report_key=REPORT_KEY)
    version = store.install(staged, report_id=report_id_for(REPORT_KEY), version="v1")
    report = repository.finish_publish(
        report_key=REPORT_KEY,
        title=staged.title,
        version="v1",
        dir_path=version.dir_path,
        manifest_sha256=staged.manifest_sha256,
        size_bytes=staged.size_bytes,
        schema_version=staged.schema_version,
        expected_current_version=None,
        request_id="request-1",
        client_ip_hash="ip-hash",
    )

    assert report.status == "published"
    assert report.current_version == "v1"
    assert report.slug.startswith("test-report-")
    assert len(report.slug.rsplit("-", 1)[1]) == 12
    bundle = repository.get_current_bundle(report.slug)
    assert bundle is not None
    assert bundle.version.dir_path == version.dir_path
    assert version.absolute_path.is_dir()


def test_republish_switches_version_and_supersedes_old(tmp_path):
    settings = _settings(tmp_path)
    store = ReportStore(settings)
    repository = ReportRepository(settings.db_path)
    repository.initialize()
    report_id = report_id_for(REPORT_KEY)

    first = store.stage(_archive(tmp_path), report_key=REPORT_KEY)
    first_ref = store.install(first, report_id=report_id, version="v1")
    first_report = repository.finish_publish(
        report_key=REPORT_KEY,
        title=first.title,
        version="v1",
        dir_path=first_ref.dir_path,
        manifest_sha256=first.manifest_sha256,
        size_bytes=first.size_bytes,
        schema_version=first.schema_version,
        expected_current_version=None,
        request_id="request-1",
        client_ip_hash="ip-hash",
    )

    second = store.stage(_archive(tmp_path), report_key=REPORT_KEY)
    second_ref = store.install(second, report_id=report_id, version="v2")
    second_report = repository.finish_publish(
        report_key=REPORT_KEY,
        title=second.title,
        version="v2",
        dir_path=second_ref.dir_path,
        manifest_sha256=second.manifest_sha256,
        size_bytes=second.size_bytes,
        schema_version=second.schema_version,
        expected_current_version="v1",
        request_id="request-2",
        client_ip_hash="ip-hash",
    )

    assert second_report.report_id == first_report.report_id
    assert second_report.slug == first_report.slug
    assert second_report.current_version == "v2"
    assert repository.get_version(report_id, "v1").status == "superseded"
    assert repository.get_version(report_id, "v2").status == "active"
    assert first_ref.absolute_path.is_dir()
    assert second_ref.absolute_path.is_dir()


def test_stale_expected_version_does_not_change_current(tmp_path):
    settings = _settings(tmp_path)
    store = ReportStore(settings)
    repository = ReportRepository(settings.db_path)
    repository.initialize()
    report_id = report_id_for(REPORT_KEY)

    staged = store.stage(_archive(tmp_path), report_key=REPORT_KEY)
    version = store.install(staged, report_id=report_id, version="v1")
    repository.finish_publish(
        report_key=REPORT_KEY,
        title=staged.title,
        version="v1",
        dir_path=version.dir_path,
        manifest_sha256=staged.manifest_sha256,
        size_bytes=staged.size_bytes,
        schema_version=staged.schema_version,
        expected_current_version=None,
        request_id="request-1",
        client_ip_hash="ip-hash",
    )

    with pytest.raises(PublishConflict):
        repository.finish_publish(
            report_key=REPORT_KEY,
            title=staged.title,
            version="v2",
            dir_path=version.dir_path,
            manifest_sha256=staged.manifest_sha256,
            size_bytes=staged.size_bytes,
            schema_version=staged.schema_version,
            expected_current_version="wrong-version",
            request_id="request-2",
            client_ip_hash="ip-hash",
        )

    assert repository.get_by_key(REPORT_KEY).current_version == "v1"


def test_unpublish_hides_public_bundle_but_keeps_version(tmp_path):
    settings = _settings(tmp_path)
    store = ReportStore(settings)
    repository = ReportRepository(settings.db_path)
    repository.initialize()

    staged = store.stage(_archive(tmp_path), report_key=REPORT_KEY)
    version = store.install(staged, report_id=report_id_for(REPORT_KEY), version="v1")
    report = repository.finish_publish(
        report_key=REPORT_KEY,
        title=staged.title,
        version="v1",
        dir_path=version.dir_path,
        manifest_sha256=staged.manifest_sha256,
        size_bytes=staged.size_bytes,
        schema_version=staged.schema_version,
        expected_current_version=None,
        request_id="request-1",
        client_ip_hash="ip-hash",
    )

    unpublished = repository.unpublish(
        report.slug, request_id="request-2", client_ip_hash="ip-hash"
    )

    assert unpublished is not None
    assert unpublished.status == "unpublished"
    assert repository.get_by_slug(report.slug) is None
    assert repository.get_by_slug(report.slug, include_unpublished=True).status == "unpublished"
    assert repository.get_current_bundle(report.slug) is None
    assert repository.get_current_bundle(report.slug, include_unpublished=True) is not None
    assert version.absolute_path.is_dir()


def test_expired_versions_can_be_removed(tmp_path):
    settings = _settings(tmp_path)
    store = ReportStore(settings)
    repository = ReportRepository(settings.db_path)
    repository.initialize()
    report_id = report_id_for(REPORT_KEY)

    first = store.stage(_archive(tmp_path), report_key=REPORT_KEY)
    first_ref = store.install(first, report_id=report_id, version="v1")
    repository.finish_publish(
        report_key=REPORT_KEY,
        title=first.title,
        version="v1",
        dir_path=first_ref.dir_path,
        manifest_sha256=first.manifest_sha256,
        size_bytes=first.size_bytes,
        schema_version=first.schema_version,
        expected_current_version=None,
        request_id="request-1",
        client_ip_hash="ip-hash",
    )
    second = store.stage(_archive(tmp_path), report_key=REPORT_KEY)
    second_ref = store.install(second, report_id=report_id, version="v2")
    repository.finish_publish(
        report_key=REPORT_KEY,
        title=second.title,
        version="v2",
        dir_path=second_ref.dir_path,
        manifest_sha256=second.manifest_sha256,
        size_bytes=second.size_bytes,
        schema_version=second.schema_version,
        expected_current_version="v1",
        request_id="request-2",
        client_ip_hash="ip-hash",
    )

    expired = repository.expired_versions(-1)

    assert [item.version for item in expired] == ["v1"]
    store.remove_version(report_id, "v1")
    repository.mark_version_deleted(report_id, "v1")
    assert not first_ref.absolute_path.exists()
    assert repository.get_version(report_id, "v1").status == "deleted"


def test_archive_rejects_path_traversal(tmp_path):
    archive = tmp_path / "bad.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("../evil.txt")
        data = b"evil"
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))

    store = ReportStore(_settings(tmp_path))

    assert _error_code(lambda: store.stage(archive, report_key=REPORT_KEY)) == (
        "ERR_PUBLISH_INVALID_ARCHIVE"
    )


def test_archive_rejects_symlink(tmp_path):
    archive = tmp_path / "symlink.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "manifest.json"
        tar.addfile(info)

    store = ReportStore(_settings(tmp_path))

    assert _error_code(lambda: store.stage(archive, report_key=REPORT_KEY)) == (
        "ERR_PUBLISH_INVALID_ARCHIVE"
    )


def test_archive_requires_manifest(tmp_path):
    store = ReportStore(_settings(tmp_path))
    archive = _archive(tmp_path, omit={"manifest.json"})

    assert _error_code(lambda: store.stage(archive, report_key=REPORT_KEY)) == (
        "ERR_PUBLISH_MANIFEST_INVALID"
    )


def test_archive_requires_referenced_assets(tmp_path):
    store = ReportStore(_settings(tmp_path))
    archive = _archive(tmp_path, omit={"assets/audio/term.mp3"})

    assert _error_code(lambda: store.stage(archive, report_key=REPORT_KEY)) == (
        "ERR_PUBLISH_ASSET_MISSING"
    )


def test_archive_rejects_unsupported_schema(tmp_path):
    store = ReportStore(_settings(tmp_path))
    manifest = _manifest()
    manifest["schema_version"] = "2.0.0"
    archive = _archive(tmp_path, manifest=manifest)

    assert _error_code(lambda: store.stage(archive, report_key=REPORT_KEY)) == (
        "ERR_PUBLISH_SCHEMA_UNSUPPORTED"
    )


def test_archive_rejects_report_key_mismatch(tmp_path):
    store = ReportStore(_settings(tmp_path))
    archive = _archive(tmp_path)

    assert _error_code(lambda: store.stage(archive, report_key="c" * 64)) == (
        "ERR_PUBLISH_MANIFEST_INVALID"
    )


def test_archive_rejects_oversized_payload(tmp_path):
    store = ReportStore(_settings(tmp_path, max_report_bytes=10))
    archive = _archive(tmp_path)

    assert _error_code(lambda: store.stage(archive, report_key=REPORT_KEY)) == (
        "ERR_PUBLISH_PAYLOAD_TOO_LARGE"
    )
