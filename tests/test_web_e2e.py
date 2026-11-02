"""End-to-end workflow across publish, rendering, media, and unpublish."""

from __future__ import annotations

import io
import json
import tarfile

from fastapi.testclient import TestClient

from situlearn.web.app import create_app
from situlearn.web.config import Settings

REPORT_KEY = "a" * 64
TOKEN = "e2e-token"


def _manifest() -> dict:
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
        "config": {},
        "narrative": {
            "title": "E2E Test Report",
            "logline": "An end-to-end test logline",
            "background": "A background paragraph for the end-to-end test.",
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


def _publish(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {TOKEN}"},
        files={"archive": ("report.tar.gz", _archive_bytes(), "application/gzip")},
        data={"report_key": REPORT_KEY, "schema_version": "1.0.0"},
    )
    assert response.status_code in {200, 201}, response.text
    return response.json()


def test_publish_render_media_repeat_and_unpublish(tmp_path):
    app = create_app(_settings(tmp_path), configure_logs=False)
    with TestClient(app) as client:
        first = _publish(client)
        slug = first["slug"]

        home = client.get(f"/r/{slug}")
        assert home.status_code == 200
        assert "E2E Test Report" in home.text
        assert "Heading 3" in home.text
        assert home.headers["content-type"].startswith("text/html")

        chapter = client.get(f"/r/{slug}/chapters/s2")
        assert chapter.status_code == 200
        assert "Spoken text for section 2." in chapter.text

        vocabulary = client.get(f"/r/{slug}/vocabulary")
        assert vocabulary.status_code == 200
        assert "中文释义内容足够长的" in vocabulary.text

        manifest = client.get(f"/r/{slug}/manifest.webmanifest")
        assert manifest.status_code == 200
        assert manifest.json()["start_url"] == f"/r/{slug}"

        full_audio = client.get(f"/r/{slug}/assets/audio/s0.mp3")
        assert full_audio.status_code == 200
        assert full_audio.content == b"section-0"

        partial_audio = client.get(
            f"/r/{slug}/assets/audio/s0.mp3",
            headers={"Range": "bytes=0-3"},
        )
        assert partial_audio.status_code == 206
        assert partial_audio.content == b"sect"

        second = _publish(client)
        assert second["slug"] == slug
        assert second["replaced"] is True

        metrics = client.get("/metrics")
        assert 'publish_total{result="success"} 2' in metrics.text
        assert "report_count 1" in metrics.text

        deleted = client.delete(
            f"/api/v1/reports/{slug}",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        assert deleted.status_code == 204

        gone = client.get(f"/r/{slug}")
        gone_audio = client.get(f"/r/{slug}/assets/audio/s0.mp3")
        assert gone.status_code == 410
        assert gone_audio.status_code == 410
