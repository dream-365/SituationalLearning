"""Tests for the document publish/lifecycle API."""

from __future__ import annotations

from pathlib import Path

from web_fixtures import (
    SECOND_TOKEN,
    TOKEN,
    client,
    document,
    media,
    multi_owner_settings,
    publish,
    settings,
)

from situlearn.web.config import Settings


def test_publish_creates_report_and_repeat_replaces(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    first = publish(test_client)
    assert first.status_code == 201, first.text
    body = first.json()
    slug = body["slug"]
    assert body["url"].endswith(f"/r/{slug}")

    second = publish(test_client)
    assert second.status_code == 200, second.text
    assert second.json()["slug"] == slug
    assert second.json()["replaced"] is True


def test_publish_requires_token(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    response = test_client.post(
        "/api/v1/reports",
        files={"archive": ("report.situ", b"x", "application/zip")},
    )
    assert response.status_code == 401


def test_publish_disabled(tmp_path: Path) -> None:
    test_client = client(
        Settings(
            data_dir=tmp_path / "data",
            backup_dir=tmp_path / "backup",
            publish_token=TOKEN,
            publish_enabled=False,
        )
    )
    response = publish(test_client)
    assert response.status_code == 503


def test_owner_metadata_and_unpublish(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    slug = publish(test_client).json()["slug"]

    metadata = test_client.get(
        f"/api/v1/reports/{slug}", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert metadata.status_code == 200
    assert metadata.json()["slug"] == slug

    public = test_client.get(f"/r/{slug}")
    assert public.status_code == 200

    deleted = test_client.delete(
        f"/api/v1/reports/{slug}", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert deleted.status_code == 204

    gone = test_client.get(f"/r/{slug}")
    assert gone.status_code == 410

    metadata = test_client.get(
        f"/api/v1/reports/{slug}", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert metadata.status_code == 200
    assert metadata.json()["status"] == "unpublished"


def test_cross_owner_isolation(tmp_path: Path) -> None:
    test_client = client(multi_owner_settings(tmp_path))
    first = publish(test_client, token=TOKEN)
    assert first.status_code == 201, first.text
    slug = first.json()["slug"]

    for method in ("get", "delete"):
        response = getattr(test_client, method)(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {SECOND_TOKEN}"},
        )
        assert response.status_code == 404

    assert test_client.get(f"/r/{slug}").status_code == 200

    second = publish(test_client, token=SECOND_TOKEN)
    assert second.status_code == 201, second.text
    assert second.json()["slug"] != slug
    assert test_client.get(f"/r/{second.json()['slug']}").status_code == 200


def test_requested_slug_and_conflict(tmp_path: Path) -> None:
    test_client = client(multi_owner_settings(tmp_path))
    first = publish(test_client, token=TOKEN, requested_slug="custom-slug")
    assert first.status_code == 201, first.text
    assert first.json()["slug"] == "custom-slug"

    conflict = publish(test_client, token=SECOND_TOKEN, requested_slug="custom-slug")
    assert conflict.status_code == 409

    invalid = publish(test_client, token=TOKEN, requested_slug="Bad Slug")
    assert invalid.status_code == 422


def test_invalid_document_rejected(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    response = publish(test_client, document_dict={})
    assert response.status_code == 422


def test_missing_asset_rejected(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    files = media()
    del files["media/audio/s0.mp3"]
    response = publish(test_client, files=files)
    assert response.status_code == 422


def test_hash_mismatch_rejected(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    files = media()
    files["media/audio/s0.mp3"] = b"tampered"
    response = publish(test_client, files=files)
    assert response.status_code == 422


def test_public_document_and_media_routes(tmp_path: Path) -> None:
    test_client = client(settings(tmp_path))
    slug = publish(test_client).json()["slug"]

    document_response = test_client.get(f"/r/{slug}/document.json")
    assert document_response.status_code == 200
    public = document_response.json()
    assert "id" not in public["meta"]
    assert "sha256" not in public["meta"]["source"]
    assert "filename" not in public["meta"]["source"]

    media_response = test_client.get(f"/r/{slug}/media/audio/s0.mp3")
    assert media_response.status_code == 200
    assert media_response.content == media()["media/audio/s0.mp3"]
    assert media_response.headers["content-type"].startswith("audio/mpeg")
    assert media_response.headers["x-content-type-options"] == "nosniff"

    legacy = test_client.get(
        f"/r/{slug}/assets/audio/s0.mp3", follow_redirects=False
    )
    assert legacy.status_code == 308
    assert legacy.headers["location"] == f"/r/{slug}/media/audio/s0.mp3"

    missing = test_client.get(f"/r/{slug}/media/audio/nope.mp3")
    assert missing.status_code == 404


def test_list_reports_is_owner_scoped(tmp_path: Path) -> None:
    test_client = client(multi_owner_settings(tmp_path))
    publish(test_client, token=TOKEN)

    listed = test_client.get(
        "/api/v1/reports", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    assert listed.status_code == 200
    assert listed.json()["count"] == 1

    other = test_client.get(
        "/api/v1/reports", headers={"Authorization": f"Bearer {SECOND_TOKEN}"}
    )
    assert other.status_code == 200
    assert other.json()["count"] == 0


def test_report_limit(tmp_path: Path) -> None:
    test_client = client(
        Settings(
            data_dir=tmp_path / "data",
            backup_dir=tmp_path / "backup",
            publish_token=TOKEN,
            max_reports=1,
        )
    )
    assert publish(test_client).status_code == 201
    second = publish(test_client, document_dict=document("b" * 64))
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "ERR_REPORT_LIMIT"


def test_publish_rate_limit(tmp_path: Path) -> None:
    test_client = client(
        Settings(
            data_dir=tmp_path / "data",
            backup_dir=tmp_path / "backup",
            publish_token=TOKEN,
            publish_rate_limit="1/min",
        )
    )
    assert publish(test_client).status_code == 201
    assert publish(test_client).status_code == 429
