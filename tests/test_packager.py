from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from situlearn.cli import main
from situlearn.document import REQUIRED_LABELS
from situlearn.packager import PackageError, package_directory
from situlearn.resolver import PackageResolver


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
    document = {
        "format": "situlearn.document",
        "version": 1,
        "meta": {
            "id": "0" * 64,
            "title": "打包测试",
            "language": "zh-CN",
            "source": {
                "filename": "a.srt",
                "sha256": "0" * 64,
                "language": "en",
                "duration_ms": 1000,
                "cue_count": 1,
            },
            "labels": labels,
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
                "blocks": [
                    {
                        "type": "group",
                        "role": "narration",
                        "script": "文稿",
                        "blocks": [
                            {"type": "image", "resource": "img-1"},
                            {"type": "text", "text": "文字"},
                            {"type": "audio", "resource": "aud-1"},
                        ],
                    }
                ],
            }
        ],
    }
    (root / "document.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return root, audio, image


def test_package_allowlists_document_and_resources(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    (root / "index.html").write_text("derived", encoding="utf-8")
    (root / ".DS_Store").write_bytes(b"junk")
    (root / "publish.json").write_text("{}", encoding="utf-8")

    info = package_directory(root, tmp_path / "report.situ")
    with zipfile.ZipFile(info.path) as archive:
        assert set(archive.namelist()) == {
            "document.json",
            "media/audio/a.mp3",
            "media/images/a.jpg",
        }
        assert archive.read("document.json") == (root / "document.json").read_bytes()
    assert any("index.html" in warning for warning in info.warnings)
    assert any(".DS_Store" in warning for warning in info.warnings)
    assert any("publish.json" in warning for warning in info.warnings)


def test_package_is_deterministic(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    first = package_directory(root, tmp_path / "a.situ")
    second = package_directory(root, tmp_path / "b.situ")
    assert first.path.read_bytes() == second.path.read_bytes()


def test_package_missing_resource(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    (root / "media" / "audio" / "a.mp3").unlink()
    with pytest.raises(PackageError) as exc:
        package_directory(root, tmp_path / "report.situ")
    assert exc.value.code == "document/missing-resource"


def test_package_hash_mismatch(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    (root / "media" / "audio" / "a.mp3").write_bytes(b"tampered")
    with pytest.raises(PackageError) as exc:
        package_directory(root, tmp_path / "report.situ")
    assert exc.value.code == "document/hash-mismatch"


def test_package_existing_output_requires_force(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    destination = tmp_path / "report.situ"
    package_directory(root, destination)
    with pytest.raises(PackageError) as exc:
        package_directory(root, destination)
    assert exc.value.code == "package/output-exists"
    package_directory(root, destination, force=True)
    assert destination.is_file()


def test_package_roundtrip_through_resolver(tmp_path: Path) -> None:
    root, audio, _ = _make_report(tmp_path)
    info = package_directory(root, tmp_path / "report.situ")
    with PackageResolver(info.path) as resolver:
        assert resolver.read("media/audio/a.mp3") == audio


def test_package_output_inside_source_rejected(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    with pytest.raises(PackageError) as exc:
        package_directory(root, root / "report.situ")
    assert exc.value.code == "package/output-inside-source"


def test_package_invalid_document(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    (root / "document.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PackageError) as exc:
        package_directory(root, tmp_path / "report.situ")
    assert exc.value.code == "document/malformed-document"


def test_cli_package(tmp_path: Path) -> None:
    root, _, _ = _make_report(tmp_path)
    destination = tmp_path / "report.situ"
    assert main(["package", str(root), "--out", str(destination)]) == 0
    assert destination.is_file()
