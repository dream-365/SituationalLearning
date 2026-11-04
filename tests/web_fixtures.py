"""Shared fixtures for document-based web tests."""

from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from situlearn.content import CATEGORY_LABELS, DOCUMENTARY_PROFILE, MOVIE_PROFILE
from situlearn.web.app import create_app
from situlearn.web.config import Settings

REPORT_KEY = "a" * 64
TOKEN = "test-token"
SECOND_TOKEN = "second-token"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def labels(kind: str = "documentary") -> dict[str, str]:
    profile = MOVIE_PROFILE if kind == "movie" else DOCUMENTARY_PROFILE
    values = dataclasses.asdict(profile.labels)
    values["vocabulary_heading"] = "生词本"
    values.update({f"category.{key}": value for key, value in CATEGORY_LABELS.items()})
    return values


def media() -> dict[str, bytes]:
    files = {f"media/audio/s{index}.mp3": f"section-{index}".encode() for index in range(4)}
    files["media/audio/term.mp3"] = b"term-audio"
    files["media/images/s0.jpg"] = b"image-bytes"
    return files


def document(
    report_key: str = REPORT_KEY,
    *,
    title: str = "Web Test Report",
    subtitle: str = "A web test logline",
    kind: str = "documentary",
) -> dict:
    files = media()
    resources = {
        f"aud-s{index}": {
            "type": "audio",
            "mime": "audio/mpeg",
            "href": f"media/audio/s{index}.mp3",
            "sha256": _sha256(files[f"media/audio/s{index}.mp3"]),
            "source": "tts",
        }
        for index in range(4)
    }
    resources["aud-term"] = {
        "type": "audio",
        "mime": "audio/mpeg",
        "href": "media/audio/term.mp3",
        "sha256": _sha256(files["media/audio/term.mp3"]),
        "source": "dictionary",
    }
    resources["img-1"] = {
        "type": "image",
        "mime": "image/jpeg",
        "href": "media/images/s0.jpg",
        "sha256": _sha256(files["media/images/s0.jpg"]),
    }
    sections = []
    for index in range(4):
        children: list[dict] = []
        if index == 0:
            children.append({"type": "image", "resource": "img-1"})
        children.append({"type": "text", "text": f"Summary {index}"})
        children.append({"type": "audio", "resource": f"aud-s{index}"})
        sections.append(
            {
                "id": f"s{index}",
                "role": "narrative",
                "title": f"Heading {index}",
                "time": {"start_ms": index * 1000, "end_ms": (index + 1) * 1000},
                "keywords": [{"word_id": "w-1"}] if index == 0 else [],
                "blocks": [
                    {
                        "type": "group",
                        "role": "narration",
                        "script": f"Spoken text for section {index}.",
                        "blocks": children,
                    }
                ],
            }
        )
    sections.append(
        {
            "id": "vocabulary",
            "role": "vocabulary",
            "title": "生词本",
            "layout": "grid",
            "blocks": [
                {
                    "id": "w-1",
                    "type": "word",
                    "term": "word",
                    "ipa": "/w/",
                    "part_of_speech": "noun",
                    "definitions": {
                        "zh": "中文释义内容足够长的",
                        "en": "English definition text",
                    },
                    "context": "A context sentence for the term.",
                    "note": "It matters because it blocks the argument.",
                    "category": "domain_term",
                    "section_id": "s0",
                    "audio": "aud-term",
                    "image": "img-1",
                    "sources": [{"name": "source", "url": "https://example.com"}],
                }
            ],
        }
    )
    return {
        "format": "situlearn.document",
        "version": 1,
        "meta": {
            "id": report_key,
            "title": title,
            "subtitle": subtitle,
            "description": "A background paragraph for rendering.",
            "language": "zh-CN",
            "kind": kind,
            "generator": {"name": "test", "version": "1"},
            "source": {
                "filename": "source.srt",
                "sha256": report_key,
                "language": "en",
                "duration_ms": 4000,
                "cue_count": 4,
            },
            "labels": labels(kind),
            "attribution": ["dictionary"],
        },
        "resources": resources,
        "sections": sections,
    }


def situ_bytes(document_dict: dict | None = None, files: dict[str, bytes] | None = None) -> bytes:
    document_dict = document() if document_dict is None else document_dict
    files = media() if files is None else files
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "document.json",
            json.dumps(document_dict, ensure_ascii=False, indent=2).encode(),
        )
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def settings(tmp_path: Path, *, token: str = TOKEN) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backup",
        publish_token=token,
        default_owner_id="owner-0001",
    )


def multi_owner_settings(tmp_path: Path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        backup_dir=tmp_path / "backup",
        publish_tokens={TOKEN: "owner-a", SECOND_TOKEN: "owner-b"},
        default_owner_id="owner-a",
    )


def client(settings_value: Settings) -> TestClient:
    return TestClient(create_app(settings_value, configure_logs=False))


def publish(
    client: TestClient,
    *,
    token: str = TOKEN,
    document_dict: dict | None = None,
    files: dict[str, bytes] | None = None,
    requested_slug: str | None = None,
    filename: str = "report.situ",
) -> object:
    data = {}
    if requested_slug is not None:
        data["requested_slug"] = requested_slug
    return client.post(
        "/api/v1/reports",
        headers={"Authorization": f"Bearer {token}"},
        files={"archive": (filename, situ_bytes(document_dict, files), "application/zip")},
        data=data,
    )
