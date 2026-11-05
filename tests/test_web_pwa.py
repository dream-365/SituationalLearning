"""Tests for PWA manifest, service worker, offline page, and icons."""

from __future__ import annotations

from pathlib import Path

from web_fixtures import TOKEN, client, publish, settings

from situlearn.web.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return settings(tmp_path, token=TOKEN)


def _client(settings_value: Settings):
    return client(settings_value)


def _publish(test_client) -> str:
    response = publish(test_client, token=TOKEN)
    assert response.status_code == 201, response.text
    return response.json()["slug"]


def test_report_manifest_is_scoped_to_report(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        slug = _publish(test_client)
        response = test_client.get(f"/r/{slug}/manifest.webmanifest")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/manifest+json")
    assert response.headers["x-robots-tag"].startswith("noindex")
    body = response.json()
    assert body["id"] == f"/r/{slug}"
    assert body["start_url"] == f"/r/{slug}"
    assert body["scope"] == f"/r/{slug}/"
    assert body["display"] == "standalone"
    assert {icon["sizes"] for icon in body["icons"]} == {"192x192", "512x512"}


def test_manifest_requires_published_report(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        missing = test_client.get("/r/missing/manifest.webmanifest")
        slug = _publish(test_client)
        test_client.delete(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        gone = test_client.get(f"/r/{slug}/manifest.webmanifest")

    assert missing.status_code == 404
    assert gone.status_code == 410


def test_service_worker_is_served_at_root_scope(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        response = test_client.get("/sw.js")

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


def test_offline_page_and_icons_are_served(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        offline = test_client.get("/offline")
        icon_192 = test_client.get("/static/icons/icon-192.png")
        icon_512 = test_client.get("/static/icons/icon-512.png")

    assert offline.status_code == 200
    assert "当前处于离线状态" in offline.text
    assert 'name="robots" content="noindex, nofollow"' in offline.text
    assert icon_192.status_code == 200
    assert icon_192.headers["content-type"] == "image/png"
    assert icon_512.status_code == 200


def test_report_page_links_its_manifest(tmp_path: Path) -> None:
    with _client(_settings(tmp_path)) as test_client:
        slug = _publish(test_client)
        page = test_client.get(f"/r/{slug}")

    assert page.status_code == 200
    assert f'/r/{slug}/manifest.webmanifest' in page.text
