"""Tests for the publish client and CLI subcommand."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from situlearn.cli import main
from situlearn.document import REQUIRED_LABELS
from situlearn.packager import package_directory
from situlearn.publish import PublishError, publish_report_dir


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _report_dir(tmp_path: Path) -> Path:
    report_dir = tmp_path / "report"
    audio = b"section-audio"
    image = b"image-bytes"
    audio_path = report_dir / "media" / "audio" / "s0.mp3"
    image_path = report_dir / "media" / "images" / "s0.jpg"
    audio_path.parent.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    audio_path.write_bytes(audio)
    image_path.write_bytes(image)
    labels = {key: f"label-{key}" for key in REQUIRED_LABELS}
    document = {
        "format": "situlearn.document",
        "version": 1,
        "meta": {
            "id": "a" * 64,
            "title": "Publish Test Report",
            "language": "zh-CN",
            "source": {
                "filename": "sample.srt",
                "sha256": "a" * 64,
                "language": "en",
                "duration_ms": 4000,
                "cue_count": 4,
            },
            "labels": labels,
            "attribution": ["Dictionary"],
        },
        "resources": {
            "aud-1": {
                "type": "audio",
                "mime": "audio/mpeg",
                "href": "media/audio/s0.mp3",
                "sha256": _sha256(audio),
                "source": "tts",
            },
            "img-1": {
                "type": "image",
                "mime": "image/jpeg",
                "href": "media/images/s0.jpg",
                "sha256": _sha256(image),
            },
        },
        "sections": [
            {
                "id": "s0",
                "role": "narrative",
                "title": "Section",
                "time": {"start_ms": 0, "end_ms": 4000},
                "blocks": [
                    {
                        "type": "group",
                        "role": "narration",
                        "script": "Spoken section text",
                        "blocks": [
                            {"type": "image", "resource": "img-1"},
                            {"type": "text", "text": "Section summary"},
                            {"type": "audio", "resource": "aud-1"},
                        ],
                    }
                ],
            }
        ],
    }
    (report_dir / "document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report_dir


def test_dry_run_packages_without_network(tmp_path):
    report_dir = _report_dir(tmp_path)

    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("dry-run must not call the network")

    result = publish_report_dir(
        report_dir,
        "https://learn.example.test",
        "",
        dry_run=True,
        transport=httpx.MockTransport(handler),
    )

    assert result.dry_run is True
    assert result.report_key == "a" * 64
    assert result.title == "Publish Test Report"
    assert result.size_bytes > 0
    assert result.slug is None


def test_upload_sends_archive_and_requested_slug(tmp_path):
    report_dir = _report_dir(tmp_path)
    (report_dir / "publish.json").write_text(
        json.dumps({"slug": "old-slug"}), encoding="utf-8"
    )
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["authorization"] = request.headers.get("authorization", "")
        seen["body"] = request.content
        return httpx.Response(
            201,
            json={
                "slug": "old-slug",
                "url": "https://learn.example.test/r/old-slug",
                "report_id": "report-id",
                "version": "v1",
                "replaced": False,
            },
        )

    result = publish_report_dir(
        report_dir,
        "https://learn.example.test",
        "secret",
        transport=httpx.MockTransport(handler),
    )

    assert seen["path"] == "/api/v1/reports"
    assert seen["authorization"] == "Bearer secret"
    body = seen["body"]
    assert isinstance(body, bytes)
    assert b"report.situ" in body
    assert b"requested_slug" in body
    assert b"old-slug" in body
    assert b"report_key" not in body
    assert result.slug == "old-slug"
    assert result.report_id == "report-id"
    assert result.version == "v1"
    assert result.replaced is False


def test_upload_situ_source(tmp_path):
    report_dir = _report_dir(tmp_path)
    package = tmp_path / "report.situ"
    package_directory(report_dir, package)

    result = publish_report_dir(
        package,
        "https://learn.example.test",
        "",
        slug="requested",
        dry_run=True,
    )

    assert result.report_key == "a" * 64
    assert result.slug == "requested"
    assert result.size_bytes == package.stat().st_size


def test_slug_argument_overrides_sidecar(tmp_path):
    report_dir = _report_dir(tmp_path)
    (report_dir / "publish.json").write_text(
        json.dumps({"slug": "sidecar-slug"}), encoding="utf-8"
    )
    result = publish_report_dir(
        report_dir,
        "https://learn.example.test",
        "",
        slug="explicit-slug",
        dry_run=True,
    )
    assert result.slug == "explicit-slug"


def test_upload_maps_unauthorized_to_exit_code_5(tmp_path):
    report_dir = _report_dir(tmp_path)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"detail": {"code": "ERR_PUBLISH_UNAUTHORIZED", "message": "no"}},
        )

    with pytest.raises(PublishError) as captured:
        publish_report_dir(
            report_dir,
            "https://learn.example.test",
            "bad",
            transport=httpx.MockTransport(handler),
        )

    assert captured.value.exit_code == 5
    assert captured.value.code == "ERR_PUBLISH_UNAUTHORIZED"


def test_upload_maps_rejection_to_exit_code_7(tmp_path):
    report_dir = _report_dir(tmp_path)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            422,
            json={"detail": {"code": "ERR_PUBLISH_INVALID_DOCUMENT", "message": "bad"}},
        )

    with pytest.raises(PublishError) as captured:
        publish_report_dir(
            report_dir,
            "https://learn.example.test",
            "secret",
            transport=httpx.MockTransport(handler),
        )

    assert captured.value.exit_code == 7
    assert captured.value.code == "ERR_PUBLISH_INVALID_DOCUMENT"


def test_upload_maps_network_error_to_exit_code_6(tmp_path):
    report_dir = _report_dir(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(PublishError) as captured:
        publish_report_dir(
            report_dir,
            "https://learn.example.test",
            "secret",
            transport=httpx.MockTransport(handler),
        )

    assert captured.value.exit_code == 6
    assert captured.value.code == "ERR_PUBLISH_NETWORK"


def test_missing_document_is_a_local_error(tmp_path):
    report_dir = tmp_path / "empty"
    report_dir.mkdir()

    with pytest.raises(PublishError) as captured:
        publish_report_dir(report_dir, "https://learn.example.test", "", dry_run=True)

    assert captured.value.exit_code == 2
    assert captured.value.code == "ERR_LOCAL_DOCUMENT"


def test_missing_asset_is_a_local_error(tmp_path):
    report_dir = _report_dir(tmp_path)
    (report_dir / "media" / "audio" / "s0.mp3").unlink()

    with pytest.raises(PublishError) as captured:
        publish_report_dir(report_dir, "https://learn.example.test", "", dry_run=True)

    assert captured.value.exit_code == 2
    assert captured.value.code == "document/missing-resource"


def test_invalid_document_is_a_local_error(tmp_path):
    report_dir = _report_dir(tmp_path)
    (report_dir / "document.json").write_text("{}", encoding="utf-8")

    with pytest.raises(PublishError) as captured:
        publish_report_dir(report_dir, "https://learn.example.test", "", dry_run=True)

    assert captured.value.exit_code == 2


def test_cli_dry_run(tmp_path, capsys):
    report_dir = _report_dir(tmp_path)

    exit_code = main(
        ["publish", str(report_dir), "--server", "https://learn.example.test", "--dry-run"]
    )

    assert exit_code == 0
    assert "dry-run:" in capsys.readouterr().out


def test_cli_missing_token_exits_5(tmp_path, monkeypatch, capsys):
    report_dir = _report_dir(tmp_path)
    monkeypatch.delenv("SITULEARN_PUBLISH_TOKEN", raising=False)

    exit_code = main(
        ["publish", str(report_dir), "--server", "https://learn.example.test"]
    )

    assert exit_code == 5
    assert "publish token is empty" in capsys.readouterr().err
