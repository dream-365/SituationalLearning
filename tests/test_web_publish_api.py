"""Tests for the publish, unpublish, and metadata API."""

from __future__ import annotations

import io
import json
import tarfile

from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.config import Settings

REPORT_KEY = "a" * 64
TOKEN = "secret-token"


def _manifest(report_key: str = REPORT_KEY, schema: str = "1.0.0") -> dict:
    return {
        "schema_version": schema,
        "source": {
            "filename": "sample.srt",
            "sha256": report_key,
            "duration_ms": 1_000,
            "cue_count": 1,
        },
        "config": {},
        "narrative": {
            "title": "API Test Report",
            "logline": "API logline",
            "background": "API background",
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


def _archive_bytes(
    *,
    manifest: dict | None = None,
    omit: set[str] | None = None,
    extra: dict[str, bytes] | None = None,
) -> bytes:
    files: dict[str, bytes] = {
        "manifest.json": json.dumps(manifest or _manifest(), ensure_ascii=False).encode(),
        "assets/audio/section.mp3": b"section-audio",
        "assets/audio/term.mp3": b"term-audio",
    }
    files.update(extra or {})
    for name in omit or set():
        files.pop(name, None)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def _settings(tmp_path, **overrides) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backup",
        publish_token=TOKEN,
        **overrides,
    )


def _client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, configure_logs=False))


def _post(
    client: TestClient,
    *,
    archive: bytes | None = None,
    report_key: str = REPORT_KEY,
    schema_version: str = "1.0.0",
    token: str | None = TOKEN,
):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(
        "/api/v1/reports",
        headers=headers,
        files={
            "archive": (
                "report.tar.gz",
                archive if archive is not None else _archive_bytes(),
                "application/gzip",
            )
        },
        data={"report_key": report_key, "schema_version": schema_version},
    )


def test_publish_creates_report_and_repeat_replaces(tmp_path):
    with _client(_settings(tmp_path)) as client:
        first = _post(client)
        assert first.status_code == 201
        first_body = first.json()
        assert first_body["replaced"] is False
        assert first_body["slug"].startswith("api-test-report-")
        assert first_body["url"].endswith(f"/r/{first_body['slug']}")

        second = _post(client)
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["replaced"] is True
        assert second_body["slug"] == first_body["slug"]
        assert second_body["report_id"] == first_body["report_id"]


def test_publish_requires_token(tmp_path):
    with _client(_settings(tmp_path)) as client:
        missing = _post(client, token=None)
        wrong = _post(client, token="wrong")

    assert missing.status_code == 401
    assert missing.json()["detail"]["code"] == "ERR_PUBLISH_UNAUTHORIZED"
    assert wrong.status_code == 401


def test_disabled_publish_returns_503(tmp_path):
    with _client(_settings(tmp_path, publish_enabled=False)) as client:
        response = _post(client)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "ERR_PUBLISH_DISABLED"


def test_admin_metadata_and_unpublish(tmp_path):
    with _client(_settings(tmp_path)) as client:
        created = _post(client)
        slug = created.json()["slug"]

        metadata = client.get(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert metadata.status_code == 200
        assert metadata.json()["status"] == "published"

        deleted = client.delete(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert deleted.status_code == 204

        after = client.get(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert after.status_code == 200
        assert after.json()["status"] == "unpublished"


def test_unknown_report_and_unauthorized_metadata(tmp_path):
    with _client(_settings(tmp_path)) as client:
        unauthorized = client.get("/api/v1/reports/missing")
        missing = client.delete(
            "/api/v1/reports/missing",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )

    assert unauthorized.status_code == 401
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "ERR_REPORT_NOT_FOUND"


def test_invalid_archive_is_rejected(tmp_path):
    bad = tarfile.TarInfo("../evil.txt")
    data = b"evil"
    bad.size = len(data)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        archive.addfile(bad, io.BytesIO(data))

    with _client(_settings(tmp_path)) as client:
        response = _post(client, archive=buffer.getvalue())

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "ERR_PUBLISH_INVALID_ARCHIVE"


def test_missing_asset_is_rejected(tmp_path):
    with _client(_settings(tmp_path)) as client:
        response = _post(
            client,
            archive=_archive_bytes(omit={"assets/audio/term.mp3"}),
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ERR_PUBLISH_ASSET_MISSING"


def test_unsupported_schema_is_rejected(tmp_path):
    with _client(_settings(tmp_path)) as client:
        response = _post(
            client,
            archive=_archive_bytes(manifest=_manifest(schema="2.0.0")),
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ERR_PUBLISH_SCHEMA_UNSUPPORTED"


def test_report_key_mismatch_is_rejected(tmp_path):
    with _client(_settings(tmp_path)) as client:
        response = _post(client, report_key="c" * 64)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ERR_PUBLISH_MANIFEST_INVALID"


def test_oversized_archive_is_rejected(tmp_path):
    with _client(_settings(tmp_path, max_report_bytes=10)) as client:
        response = _post(client)

    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "ERR_PUBLISH_PAYLOAD_TOO_LARGE"


def test_publish_rate_limit(tmp_path):
    with _client(_settings(tmp_path)) as client:
        responses = [_post(client) for _ in range(6)]

    assert responses[0].status_code == 201
    assert responses[5].status_code == 429
    assert responses[5].json()["detail"]["code"] == "ERR_RATE_LIMITED"
