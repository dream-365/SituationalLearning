from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from situlearn.resolver import (
    DirectoryResolver,
    HttpResolver,
    PackageResolver,
    ResourceNotFound,
    UnsafePackage,
    UnsafeResource,
)


def _write_zip(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)


def test_directory_resolver_reads_and_blocks_escape(tmp_path: Path) -> None:
    media = tmp_path / "media" / "audio" / "a.mp3"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"audio")
    resolver = DirectoryResolver(tmp_path)
    assert resolver.read("media/audio/a.mp3") == b"audio"
    with pytest.raises(ResourceNotFound):
        resolver.read("media/audio/missing.mp3")
    with pytest.raises(UnsafeResource):
        resolver.read("media/../secret.mp3")
    with pytest.raises(UnsafeResource):
        resolver.read("assets/audio/a.mp3")


def test_directory_resolver_rejects_symlink_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-audio.mp3"
    outside.write_bytes(b"outside")
    link = tmp_path / "media" / "link.mp3"
    link.parent.mkdir(parents=True)
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlink not supported")
    resolver = DirectoryResolver(tmp_path)
    with pytest.raises(UnsafeResource):
        resolver.path("media/link.mp3")


def test_package_resolver_reads_and_rejects_unsafe_entries(tmp_path: Path) -> None:
    archive_path = tmp_path / "report.situ"
    _write_zip(
        archive_path,
        {
            "document.json": b"{}",
            "media/audio/a.mp3": b"audio",
        },
    )
    with PackageResolver(archive_path) as resolver:
        assert resolver.read("media/audio/a.mp3") == b"audio"
        with pytest.raises(ResourceNotFound):
            resolver.read("media/audio/missing.mp3")

    unsafe_path = tmp_path / "unsafe.situ"
    _write_zip(unsafe_path, {"../evil": b"x"})
    with pytest.raises(UnsafePackage):
        PackageResolver(unsafe_path)

    symlink_path = tmp_path / "symlink.situ"
    info = zipfile.ZipInfo("media/link")
    info.external_attr = 0o120777 << 16
    with zipfile.ZipFile(symlink_path, "w") as archive:
        archive.writestr(info, "target")
    with pytest.raises(UnsafePackage):
        PackageResolver(symlink_path)


def test_http_resolver_keeps_document_origin() -> None:
    resolver = HttpResolver("https://host/r/slug/document.json")
    assert resolver.url("media/audio/a.mp3") == "https://host/r/slug/media/audio/a.mp3"
    with pytest.raises(UnsafeResource):
        resolver.url("https://evil.example/x.mp3")
    with pytest.raises(UnsafeResource):
        resolver.url("media/../secret.mp3")
    with pytest.raises(UnsafeResource):
        resolver.url("assets/audio/a.mp3")


def test_same_document_resolves_in_all_modes(tmp_path: Path) -> None:
    media = tmp_path / "media" / "audio" / "a.mp3"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"audio")
    archive_path = tmp_path / "report.situ"
    _write_zip(archive_path, {"document.json": b"{}", "media/audio/a.mp3": b"audio"})

    directory = DirectoryResolver(tmp_path)
    with PackageResolver(archive_path) as package:
        http = HttpResolver("https://host/r/slug/document.json")
        assert directory.read("media/audio/a.mp3") == package.read("media/audio/a.mp3")
        assert http.url("media/audio/a.mp3").endswith("/r/slug/media/audio/a.mp3")
