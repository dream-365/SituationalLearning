"""Tests for PWA manifest, service worker, offline page, and icons."""

from __future__ import annotations

import io
import json
import tarfile

from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.config import Settings

REPORT_KEY = "a" * 64
TOKEN = "pwa-token"


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
            "title": "PWA Test Report",
            "logline": "A PWA test logline",
            "background": "A background paragraph for PWA testing.",
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


def test_report_manifest_is_scoped_to_report(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        response = client.get(f"/r/{slug}/manifest.webmanifest")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")
    assert response.headers["x-robots-tag"].startswith("noindex")
    body = response.json()
    assert body["id"] == f"/r/{slug}"
    assert body["start_url"] == f"/r/{slug}"
    assert body["scope"] == f"/r/{slug}/"
    assert body["display"] == "standalone"
    assert {icon["sizes"] for icon in body["icons"]} == {"192x192", "512x512"}


def test_manifest_requires_published_report(tmp_path):
    with _client(_settings(tmp_path)) as client:
        missing = client.get("/r/missing/manifest.webmanifest")
        slug = _publish(client)
        client.delete(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        gone = client.get(f"/r/{slug}/manifest.webmanifest")

    assert missing.status_code == 404
    assert gone.status_code == 410


def test_service_worker_is_served_at_root_scope(tmp_path):
    with _client(_settings(tmp_path)) as client:
        response = client.get("/sw.js")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/javascript")
    assert response.headers["service-worker-allowed"] == "/"
    text = response.text
    assert 'const VERSION = "v1"' in text
    assert "/offline" in text
    assert "/static/styles.css" in text
    assert "/static/player.js" in text
    assert "MAX_RUNTIME_ENTRIES = 200" in text
    assert "self.skipWaiting()" in text
    assert "self.clients.claim()" in text


def test_offline_page_and_icons_are_served(tmp_path):
    with _client(_settings(tmp_path)) as client:
        offline = client.get("/offline")
        icon_192 = client.get("/static/icons/icon-192.png")
        icon_512 = client.get("/static/icons/icon-512.png")

    assert offline.status_code == 200
    assert "当前处于离线状态" in offline.text
    assert 'name="robots" content="noindex, nofollow"' in offline.text
    assert icon_192.status_code == 200
    assert icon_192.headers["content-type"] == "image/png"
    assert icon_512.status_code == 200


def test_report_page_links_its_manifest(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        page = client.get(f"/r/{slug}")

    assert page.status_code == 200
    assert f'/r/{slug}/manifest.webmanifest' in page.text
