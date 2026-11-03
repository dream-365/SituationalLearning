"""Tests for the web service foundation: settings, health, and logging."""

from __future__ import annotations

import json
import logging

from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.config import Settings
from situlearn.web.observability import JsonFormatter


def _settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", backup_dir=tmp_path / "backup")


def test_healthz_returns_ok_and_request_id(tmp_path):
    app = create_app(_settings(tmp_path), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"X-Request-ID": "test-request-1"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request-1"


def test_healthz_replaces_invalid_request_id(tmp_path):
    app = create_app(_settings(tmp_path), configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/healthz", headers={"X-Request-ID": "bad id"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad id"
    assert len(response.headers["X-Request-ID"]) == 32


def test_readyz_creates_data_directories(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"data_dir": "ok", "object_store": "ok"},
    }
    assert settings.reports_dir.is_dir()
    assert settings.staging_dir.is_dir()
    assert settings.trash_dir.is_dir()


def test_readyz_returns_503_when_data_dir_is_a_file(tmp_path):
    data_path = tmp_path / "data"
    data_path.write_text("not a directory", encoding="utf-8")
    settings = Settings(data_dir=data_path, backup_dir=tmp_path / "backup")
    app = create_app(settings, configure_logs=False)
    with TestClient(app) as client:
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["status"] == "unready"
    assert response.json()["checks"]["data_dir"].startswith("error:")


def test_settings_from_env_reads_overrides(tmp_path):
    env = {
        "SITULEARN_DATA_DIR": str(tmp_path / "data"),
        "SITULEARN_BACKUP_DIR": str(tmp_path / "backup"),
        "SITE_BASE_URL": "https://learn.example.test/",
        "PUBLISH_ENABLED": "false",
        "MAX_REPORT_BYTES": "1234",
        "MAX_REPORTS": "7",
        "LOG_LEVEL": "DEBUG",
    }

    settings = Settings.from_env(env)

    assert settings.data_dir == tmp_path / "data"
    assert settings.backup_dir == tmp_path / "backup"
    assert settings.site_base_url == "https://learn.example.test"
    assert settings.publish_enabled is False
    assert settings.max_report_bytes == 1234
    assert settings.max_reports == 7
    assert settings.log_level == "debug"
    assert settings.db_path == tmp_path / "data" / "situlearn.sqlite3"


def test_json_formatter_emits_one_object_per_record():
    record = logging.LogRecord(
        name="situlearn.web",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request",
        args=(),
        exc_info=None,
    )
    record.status = 200

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "info"
    assert payload["message"] == "request"
    assert payload["status"] == 200
    assert payload["request_id"] == "-"
