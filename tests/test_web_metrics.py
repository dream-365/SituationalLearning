"""Tests for metrics exposition and backup rotation."""

from __future__ import annotations

import io
import json
import os
import tarfile
import time

import pytest
from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.backup import create_backup
from situlearn.web.backup import main as backup_main
from situlearn.web.config import Settings

REPORT_KEY = "a" * 64
TOKEN = "metrics-token"


def _manifest() -> dict:
    sections = [
        {
            "section_id": f"s{index}",
            "heading": f"Heading {index}",
            "start_ms": index * 1_000,
            "end_ms": (index + 1) * 1_000,
            "summary": f"Summary {index}",
            "key_terms": [],
            "spoken_text": f"Spoken text for section {index}.",
            "audio_refs": [f"assets/audio/s{index}.mp3"],
            "audio_status": "ready",
        }
        for index in range(4)
    ]
    return {
        "schema_version": "1.0.0",
        "source": {
            "filename": "source.srt",
            "sha256": REPORT_KEY,
            "duration_ms": 4_000,
            "cue_count": 4,
        },
        "config": {},
        "narrative": {
            "title": "Metrics Test Report",
            "logline": "A metrics test logline",
            "background": "A background paragraph for metrics.",
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


def _archive_bytes() -> bytes:
    files = {
        "manifest.json": json.dumps(_manifest(), ensure_ascii=False).encode(),
        "assets/audio/term.mp3": b"term-audio",
    }
    for index in range(4):
        files[f"assets/audio/s{index}.mp3"] = f"section-{index}".encode()
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backup",
        publish_token=TOKEN,
    )


def _client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, configure_logs=False))


def _publish(client: TestClient) -> str:
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files={"archive": ("report.tar.gz", _archive_bytes(), "application/gzip")},
        data={"report_key": REPORT_KEY, "schema_version": "1.0.0"},
    )
    assert response.status_code == 201, response.text
    return response.json()["slug"]


def _metric_value(text: str, name: str) -> float:
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.rsplit(" ", 1)[1])
    raise AssertionError(f"metric not found: {name}")


def test_metrics_endpoint_exposes_expected_names(tmp_path):
    with _client(_settings(tmp_path)) as client:
        client.get("/healthz")
        response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.headers["x-robots-tag"].startswith("noindex")
    text = response.text
    for name in (
        "http_requests_total",
        "http_request_duration_seconds_sum",
        "http_request_duration_seconds_count",
        "publish_total",
        "report_count",
        "storage_bytes",
    ):
        assert name in text


def test_http_and_publish_metrics_update_after_requests(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        client.get(f"/r/{slug}")
        response = client.get("/metrics")

    text = response.text
    assert 'http_requests_total{method="GET",status="200"} ' in text
    assert 'publish_total{result="success"} 1' in text
    assert _metric_value(text, "report_count") == 1
    assert _metric_value(text, "storage_bytes") > 0
    assert _metric_value(text, "http_request_duration_seconds_count") >= 2


def test_failed_requests_are_counted(tmp_path):
    with _client(_settings(tmp_path)) as client:
        client.get("/r/missing")
        response = client.get("/metrics")

    assert 'http_requests_total{method="GET",status="404"} ' in response.text


def test_backup_creates_archive_with_database_and_reports(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backup"
    (data_dir / "reports" / "r1").mkdir(parents=True)
    (data_dir / "situlearn.sqlite3").write_bytes(b"sqlite")
    (data_dir / "reports" / "r1" / "manifest.json").write_text("{}", encoding="utf-8")

    archive = create_backup(data_dir, backup_dir)

    assert archive.is_file()
    with tarfile.open(archive, "r:gz") as tar:
        names = set(tar.getnames())
    assert "situlearn.sqlite3" in names
    assert "reports/r1/manifest.json" in names


def test_backup_prunes_archives_older_than_retention(tmp_path):
    data_dir = tmp_path / "data"
    backup_dir = tmp_path / "backup"
    data_dir.mkdir()
    backup_dir.mkdir()
    (data_dir / "situlearn.sqlite3").write_bytes(b"sqlite")
    old = backup_dir / "situlearn-20200101T000000Z.tar.gz"
    old.write_bytes(b"old")
    old_time = time.time() - 10 * 86_400
    os.utime(old, (old_time, old_time))

    archive = create_backup(data_dir, backup_dir, keep_days=7, now=time.time())

    assert archive.is_file()
    assert not old.exists()


def test_backup_rejects_missing_data_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "missing", tmp_path / "backup")


def test_backup_cli(tmp_path, capsys):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "situlearn.sqlite3").write_bytes(b"sqlite")

    exit_code = backup_main(
        ["--data-dir", str(data_dir), "--backup-dir", str(tmp_path / "backup")]
    )

    assert exit_code == 0
    assert "situlearn-" in capsys.readouterr().out
