"""Tests for the local publish client and CLI subcommand."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from situlearn.cli import main
from situlearn.publish import PublishError, publish_report_dir


def _manifest(report_key: str = "a" * 64) -> dict:
    sections = [
        {
            "section_id": f"s{index}",
            "heading": f"Heading {index}",
            "start_ms": index * 1_000,
            "end_ms": (index + 1) * 1_000,
            "summary": "Section summary",
            "key_terms": [],
            "spoken_text": "Spoken section text",
            "audio_refs": [f"assets/audio/s{index}.mp3"],
            "audio_status": "ready",
        }
        for index in range(4)
    ]
    return {
        "schema_version": "1.0.0",
        "source": {
            "filename": "sample.srt",
            "sha256": report_key,
            "duration_ms": 4_000,
            "cue_count": 4,
        },
        "config": {},
        "narrative": {
            "title": "Publish Test Report",
            "logline": "A publish test logline",
            "background": "A background paragraph for the publish test.",
            "sections": sections,
        },
        "terms": [
            {
                "term": "word",
                "ipa": "/w/",
                "part_of_speech": "noun",
                "definition_zh": "中文释义内容足够长的",
                "definition_en": "English definition text",
                "context_sentence": "A context sentence for the term.",
                "why_it_matters": "It matters because it blocks the argument.",
                "section_id": "s0",
                "category": "domain_term",
                "audio_ref": "assets/audio/term.mp3",
                "audio_source": "dictionary",
                "sources": [{"name": "source", "url": "https://example.com"}],
            }
        ],
        "assets": [
            {
                "asset_id": f"a{index}",
                "path": f"assets/audio/s{index}.mp3",
                "duration_ms": 1_000,
                "text_sha256": "b" * 64,
                "source": "tts",
            }
            for index in range(4)
        ],
        "warnings": [],
    }


def _report_dir(tmp_path: Path) -> Path:
    report_dir = tmp_path / "report"
    audio = report_dir / "assets" / "audio"
    audio.mkdir(parents=True)
    (report_dir / "manifest.json").write_text(
        json.dumps(_manifest(), ensure_ascii=False), encoding="utf-8"
    )
    for index in range(4):
        (audio / f"s{index}.mp3").write_bytes(f"section-{index}".encode())
    (audio / "term.mp3").write_bytes(b"term-audio")
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


def test_upload_sends_token_and_returns_result(tmp_path):
    report_dir = _report_dir(tmp_path)
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["authorization"] = request.headers.get("authorization", "")
        return httpx.Response(
            201,
            json={
                "slug": "publish-test-report-abcdefghijk2",
                "url": "https://learn.example.test/r/publish-test-report-abcdefghijk2",
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

    assert seen == {
        "path": "/api/v1/reports",
        "authorization": "Bearer secret",
    }
    assert result.slug == "publish-test-report-abcdefghijk2"
    assert result.url.endswith("/r/publish-test-report-abcdefghijk2")
    assert result.report_id == "report-id"
    assert result.version == "v1"
    assert result.replaced is False


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
            json={"detail": {"code": "ERR_PUBLISH_ASSET_MISSING", "message": "missing"}},
        )

    with pytest.raises(PublishError) as captured:
        publish_report_dir(
            report_dir,
            "https://learn.example.test",
            "secret",
            transport=httpx.MockTransport(handler),
        )

    assert captured.value.exit_code == 7
    assert captured.value.code == "ERR_PUBLISH_ASSET_MISSING"


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


def test_missing_manifest_is_a_local_error(tmp_path):
    report_dir = tmp_path / "empty"
    report_dir.mkdir()

    with pytest.raises(PublishError) as captured:
        publish_report_dir(report_dir, "https://learn.example.test", "", dry_run=True)

    assert captured.value.exit_code == 2


def test_missing_asset_is_a_local_error(tmp_path):
    report_dir = _report_dir(tmp_path)
    (report_dir / "assets" / "audio" / "s2.mp3").unlink()

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
