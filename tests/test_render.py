from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from situlearn.cli import main
from situlearn.document import REQUIRED_LABELS
from situlearn.packager import package_directory
from situlearn.render import RenderError, render_document


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_report(tmp_path: Path) -> tuple[Path, bytes, bytes]:
    root = tmp_path / "report"
    audio = b"audio-bytes"
    image = b"image-bytes"
    audio_path = root / "media" / "audio" / "a.mp3"
    image_path = root / "media" / "images" / "a.jpg"
    audio_path.parent.mkdir(parents=True)
    image_path.parent.mkdir(parents=True)
    audio_path.write_bytes(audio)
    image_path.write_bytes(image)
    labels = {key: f"label-{key}" for key in REQUIRED_LABELS}
    labels["no_audio"] = "暂无音频"
    document = {
        "format": "situlearn.document",
        "version": 1,
        "meta": {
            "id": "0" * 64,
            "title": "渲染测试",
            "subtitle": "副标题",
            "description": "背景说明",
            "language": "zh-CN",
            "source": {
                "filename": "a.srt",
                "sha256": "0" * 64,
                "language": "en",
                "duration_ms": 1000,
                "cue_count": 1,
            },
            "labels": labels,
            "attribution": ["Dictionary"],
        },
        "resources": {
            "aud-1": {
                "type": "audio",
                "mime": "audio/mpeg",
                "href": "media/audio/a.mp3",
                "sha256": _sha256(audio),
                "source": "tts",
            },
            "img-1": {
                "type": "image",
                "mime": "image/jpeg",
                "href": "media/images/a.jpg",
                "sha256": _sha256(image),
            },
        },
        "sections": [
            {
                "id": "s1",
                "role": "narrative",
                "title": "第一节",
                "time": {"start_ms": 0, "end_ms": 1000},
                "keywords": [{"word_id": "w-1"}],
                "blocks": [
                    {
                        "type": "group",
                        "role": "narration",
                        "script": "<script>alert(1)</script>",
                        "blocks": [
                            {"type": "image", "resource": "img-1"},
                            {"type": "text", "text": "<b>文字</b>"},
                            {"type": "audio", "resource": "aud-1"},
                        ],
                    }
                ],
            },
            {
                "id": "vocabulary",
                "role": "vocabulary",
                "title": "生词本",
                "layout": "grid",
                "blocks": [
                    {
                        "id": "w-1",
                        "type": "word",
                        "term": "<script>term</script>",
                        "ipa": "/test/",
                        "part_of_speech": "noun",
                        "definitions": {"zh": "<b>释义</b>", "en": "definition"},
                        "context": "context sentence",
                        "note": "note",
                        "category": "domain_term",
                        "section_id": "s1",
                        "audio": "aud-1",
                        "image": "img-1",
                        "sources": [
                            {"name": "DeepSeek 语境释义", "url": "https://api.deepseek.com"},
                            {"name": "Wiktionary", "url": "https://example.com"},
                        ],
                    }
                ],
            },
        ],
    }
    (root / "document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return root, audio, image


def test_render_directory_escapes_and_copies_media(tmp_path: Path) -> None:
    root, audio, image = _make_report(tmp_path)
    out = tmp_path / "html"
    info = render_document(root, out)
    html = (out / "index.html").read_text(encoding="utf-8")

    assert info.sections == 2
    assert info.blocks == 5
    assert info.missing == ()
    assert (out / "media" / "audio" / "a.mp3").read_bytes() == audio
    assert (out / "media" / "images" / "a.jpg").read_bytes() == image
    assert not (out / "document.json").exists()
    assert "<audio" in html and "<img" in html
    assert "data-play-section" in html
    assert 'data-category-filter="domain_term"' in html
    assert 'data-section-filter' in html
    assert 'data-word-search' in html
    assert 'data-category="domain_term"' in html
    assert 'data-section-id="s1"' in html
    assert 'data-word-count' in html
    assert 'data-vocab-group="domain_term"' in html
    assert "word-audio" in html
    assert "word-origin" in html
    assert 'class="toc"' in html
    assert 'data-group-more' in html
    assert "vocab-group-head" in html
    assert "&lt;b&gt;文字&lt;/b&gt;" in html
    assert "&lt;script&gt;term&lt;/script&gt;" in html
    assert "&lt;b&gt;释义&lt;/b&gt;" in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<b>文字</b>" not in html
    assert "<script>term</script>" not in html
    assert "DeepSeek 语境释义" not in html
    assert "Wiktionary" in html


def test_render_situ_package(tmp_path: Path) -> None:
    root, audio, _ = _make_report(tmp_path)
    package = tmp_path / "report.situ"
    package_directory(root, package)
    out = tmp_path / "html"
    info = render_document(package, out)
    assert info.sections == 2
    assert (out / "media" / "audio" / "a.mp3").read_bytes() == audio
    assert (out / "index.html").is_file()


def test_render_missing_media_degrades(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    (root / "media" / "audio" / "a.mp3").unlink()
    out = tmp_path / "html"
    info = render_document(root, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "media/audio/a.mp3" in info.missing
    assert "暂无音频" in html


def test_render_hash_mismatch_degrades(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    (root / "media" / "audio" / "a.mp3").write_bytes(b"tampered")
    out = tmp_path / "html"
    info = render_document(root, out)
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "media/audio/a.mp3" in info.missing
    assert "暂无音频" in html


def test_render_output_must_be_empty(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    out = tmp_path / "html"
    out.mkdir()
    (out / "existing.txt").write_text("x", encoding="utf-8")
    with pytest.raises(RenderError) as exc:
        render_document(root, out)
    assert exc.value.code == "render/output-not-empty"


def test_render_output_inside_source_rejected(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    with pytest.raises(RenderError) as exc:
        render_document(root, root / "html")
    assert exc.value.code == "render/output-inside-source"


def test_cli_render(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    out = tmp_path / "html"
    assert main(["render", str(root), "--out", str(out)]) == 0
    assert (out / "index.html").is_file()
