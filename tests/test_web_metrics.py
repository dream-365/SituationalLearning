"""Tests for metrics exposition and backup rotation."""

from __future__ import annotations

import os
import tarfile
import time
from pathlib import Path

import pytest
from web_fixtures import TOKEN, client, publish, settings

from situlearn.web.backup import create_backup
from situlearn.web.backup import main as backup_main
from situlearn.web.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return settings(tmp_path, token=TOKEN)


def _client(settings_value: Settings):
    return client(settings_value)


def _publish(test_client) -> str:
    response = publish(test_client, token=TOKEN)
    assert response.status_code == 201, response.text
    return response.json()["slug"]


def _metric_value(text: str, name: str) -> float:
    for line in text.splitlines():
        if line.startswith(name + " "):
            return float(line.rsplit(" ", 1)[1])
    raise AssertionError(f"metric not found: {name}")


def test_metrics_endpoint_exposes_expected_names(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        test_client.get("/healthz")
        response = test_client.get("/metrics")

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


def test_http_and_publish_metrics_update_after_requests(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        slug = _publish(test_client)
        test_client.get(f"/r/{slug}")
        response = test_client.get("/metrics")

    text = response.text
    assert 'http_requests_total{method="GET",status="200"} ' in text
    assert 'publish_total{result="success"} 1' in text
    assert _metric_value(text, "report_count") == 1
    assert _metric_value(text, "storage_bytes") > 0
    assert _metric_value(text, "http_request_duration_seconds_count") >= 2


def test_failed_requests_are_counted(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        test_client.get("/r/missing")
        response = test_client.get("/metrics")

    assert 'http_requests_total{method="GET",status="404"} ' in response.text


def test_backup_creates_archive_with_database_and_reports(tmp_path: Path) -> None:
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


def test_backup_prunes_archives_older_than_retention(tmp_path: Path) -> None:
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


def test_backup_rejects_missing_data_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        create_backup(tmp_path / "missing", tmp_path / "backup")


def test_backup_cli(tmp_path: Path, capsys) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "situlearn.sqlite3").write_bytes(b"sqlite")

    exit_code = backup_main(
        ["--data-dir", str(data_dir), "--backup-dir", str(tmp_path / "backup")]
    )

    assert exit_code == 0
    assert "situlearn-" in capsys.readouterr().out
