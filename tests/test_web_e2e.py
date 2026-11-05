"""End-to-end document publishing, viewing, and unpublishing."""

from __future__ import annotations

from pathlib import Path

from web_fixtures import TOKEN, client, media, publish, settings


def test_publish_render_media_repeat_and_unpublish(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    first = publish(test_client)
    assert first.status_code == 201, first.text
    slug = first.json()["slug"]

    home = test_client.get(f"/r/{slug}")
    assert home.status_code == 200
    assert "Web Test Report" in home.text
    assert 'id="word-w-1"' in home.text

    manifest = test_client.get(f"/r/{slug}/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.json()["start_url"] == f"/r/{slug}"

    document = test_client.get(f"/r/{slug}/document.json")
    assert document.status_code == 200
    assert "id" not in document.json()["meta"]

    audio = test_client.get(f"/r/{slug}/media/audio/s0.mp3")
    assert audio.status_code == 200
    assert audio.content == media()["media/audio/s0.mp3"]

    assert test_client.delete(
        f"/api/v1/reports/{slug}",
        headers={"Authorization": f"Bearer {TOKEN}"},
    ).status_code == 204
    assert test_client.get(f"/r/{slug}").status_code == 410
    assert test_client.get(f"/r/{slug}/media/audio/s0.mp3").status_code == 410

    again = publish(test_client)
    assert again.status_code == 200
    assert again.json()["slug"] == slug
    assert test_client.get(f"/r/{slug}").status_code == 200
