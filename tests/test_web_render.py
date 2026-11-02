"""Tests for server-rendered public report pages."""

from __future__ import annotations

import io
import json
import tarfile

from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.config import Settings

REPORT_KEY = "a" * 64
TOKEN = "render-token"


def _manifest(title: str = "Render Test Report") -> dict:
    sections = [
        {
            "section_id": f"s{index}",
            "heading": f"Heading {index}",
            "start_ms": index * 1_000,
            "end_ms": (index + 1) * 1_000,
            "summary": f"Summary {index}",
            "key_terms": ["word"] if index == 0 else [],
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
        "config": {"llm_model": "test-model"},
        "narrative": {
            "title": title,
            "logline": "A render test logline",
            "background": "A background paragraph for rendering.",
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


def test_report_home_renders_public_content(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        response = client.get(f"/r/{slug}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    html = response.text
    assert "Render Test Report" in html
    assert "Heading 0" in html
    assert "查看词表" in html
    assert "播放本节" in html
    assert "source.srt" not in html
    assert "test-model" not in html
    assert REPORT_KEY not in html
    assert "report_id" not in html


def test_chapter_page_renders_spoken_text(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        response = client.get(f"/r/{slug}/chapters/s1")
        missing = client.get(f"/r/{slug}/chapters/nope")

    assert response.status_code == 200
    assert "Spoken text for section 1." in response.text
    assert "Heading 1" in response.text
    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "ERR_REPORT_NOT_FOUND"


def test_vocabulary_page_renders_and_filters(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        all_terms = client.get(f"/r/{slug}/vocabulary")
        matching = client.get(f"/r/{slug}/vocabulary?q=word")
        missing = client.get(f"/r/{slug}/vocabulary?q=absent")
        by_section = client.get(f"/r/{slug}/vocabulary?section=s0")
        by_wrong_section = client.get(f"/r/{slug}/vocabulary?section=s3")
        by_category = client.get(f"/r/{slug}/vocabulary?category=domain_term")
        by_wrong_category = client.get(f"/r/{slug}/vocabulary?category=proper_noun")

    assert all_terms.status_code == 200
    assert "中文释义内容足够长的" in all_terms.text
    assert "It matters because it blocks the argument." in all_terms.text
    assert "word" in matching.text
    assert "word" not in missing.text
    assert "没有符合条件的词条。" in missing.text
    assert "word" in by_section.text
    assert "word" not in by_wrong_section.text
    assert "word" in by_category.text
    assert "word" not in by_wrong_category.text


def test_unknown_report_returns_404_and_unpublished_returns_410(tmp_path):
    with _client(_settings(tmp_path)) as client:
        missing = client.get("/r/does-not-exist")
        slug = _publish(client)
        deleted = client.delete(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        gone = client.get(f"/r/{slug}")

    assert missing.status_code == 404
    assert deleted.status_code == 204
    assert gone.status_code == 410
    assert gone.json()["detail"]["code"] == "ERR_REPORT_GONE"


def test_asset_serves_audio_with_range(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        full = client.get(f"/r/{slug}/assets/audio/s0.mp3")
        partial = client.get(
            f"/r/{slug}/assets/audio/s0.mp3",
            headers={"Range": "bytes=0-3"},
        )

    assert full.status_code == 200
    assert full.headers["content-type"] == "audio/mpeg"
    assert full.content == b"section-0"
    assert partial.status_code == 206
    assert partial.headers["content-range"].startswith("bytes 0-3/")
    assert partial.content == b"sect"


def test_public_headers_and_head_request(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        response = client.get(f"/r/{slug}")
        head = client.head(f"/r/{slug}")

    assert response.headers["x-robots-tag"] == "noindex, nofollow"
    assert response.headers["strict-transport-security"].startswith("max-age=31536000")
    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert head.status_code == 200
    assert head.headers["x-robots-tag"] == "noindex, nofollow"


def test_asset_path_traversal_is_rejected(tmp_path):
    with _client(_settings(tmp_path)) as client:
        slug = _publish(client)
        response = client.get(f"/r/{slug}/assets/%2e%2e/manifest.json")

    assert response.status_code in {400, 404}
