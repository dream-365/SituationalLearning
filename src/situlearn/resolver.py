"""Resolve ``media/...`` document hrefs for directory, .situ, and HTTP bases."""

from __future__ import annotations

import unicodedata
import zipfile
from pathlib import Path, PurePosixPath
from typing import Self
from urllib.parse import urljoin, urlsplit

import httpx

from situlearn.document import href_issue


class ResourceNotFound(LookupError):
    """The referenced resource does not exist."""


class UnsafeResource(ValueError):
    """The href is unsafe or escapes its base."""


class UnsafePackage(ValueError):
    """The .situ archive contains an unsafe entry."""


def _checked_href(href: str) -> None:
    issue = href_issue(href)
    if issue:
        raise UnsafeResource(issue)


def _zip_name_issue(name: str) -> str | None:
    if not name:
        return "entry name is empty"
    if "\\" in name:
        return "entry name must use '/'"
    if "\x00" in name:
        return "entry name contains NUL"
    if name.startswith("/"):
        return "entry name must be relative"
    if "//" in name:
        return "entry name contains an empty segment"
    if unicodedata.normalize("NFC", name) != name:
        return "entry name must be NFC-normalized"
    parts = PurePosixPath(name).parts
    if any(part in {"", ".", ".."} for part in parts):
        return "entry name contains an unsafe segment"
    return None


class DirectoryResolver:
    """Resolve hrefs against an unpacked document directory."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, href: str) -> Path:
        _checked_href(href)
        candidate = (self.root / href).resolve()
        if not candidate.is_relative_to(self.root):
            raise UnsafeResource(f"href escapes the document root: {href!r}")
        return candidate

    def read(self, href: str) -> bytes:
        path = self.path(href)
        if not path.is_file():
            raise ResourceNotFound(href)
        return path.read_bytes()


class PackageResolver:
    """Resolve hrefs inside a .situ zip archive."""

    def __init__(self, archive_path: Path) -> None:
        self.archive_path = archive_path
        self._archive = zipfile.ZipFile(archive_path, "r")
        self._names: set[str] = set()
        try:
            for info in self._archive.infolist():
                issue = _zip_name_issue(info.filename)
                if issue:
                    raise UnsafePackage(f"{info.filename!r}: {issue}")
                if info.filename in self._names:
                    raise UnsafePackage(f"duplicate entry: {info.filename!r}")
                if (info.external_attr >> 16) & 0o170000 == 0o120000:
                    raise UnsafePackage(f"symlink entry: {info.filename!r}")
                self._names.add(info.filename)
        except Exception:
            self._archive.close()
            raise

    @property
    def names(self) -> frozenset[str]:
        return frozenset(self._names)

    def read(self, href: str) -> bytes:
        _checked_href(href)
        if href not in self._names:
            raise ResourceNotFound(href)
        return self._archive.read(href)

    def read_entry(self, name: str) -> bytes:
        """Read a non-media entry such as ``document.json``."""

        if name not in self._names:
            raise ResourceNotFound(name)
        return self._archive.read(name)

    def close(self) -> None:
        self._archive.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class HttpResolver:
    """Resolve hrefs against the public document URL."""

    def __init__(self, document_url: str) -> None:
        parsed = urlsplit(document_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("document_url must be an absolute http(s) URL")
        self.document_url = document_url
        self._scheme = parsed.scheme
        self._netloc = parsed.netloc

    def url(self, href: str) -> str:
        _checked_href(href)
        resolved = urljoin(self.document_url, href)
        parsed = urlsplit(resolved)
        if parsed.scheme != self._scheme or parsed.netloc != self._netloc:
            raise UnsafeResource(f"href escapes the document origin: {href!r}")
        return resolved

    def read(self, href: str, *, timeout: float = 30.0) -> bytes:
        response = httpx.get(self.url(href), timeout=timeout)
        response.raise_for_status()
        return response.content


__all__ = [
    "DirectoryResolver",
    "HttpResolver",
    "PackageResolver",
    "ResourceNotFound",
    "UnsafePackage",
    "UnsafeResource",
]
