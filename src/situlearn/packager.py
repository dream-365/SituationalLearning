"""Build deterministic, allowlisted .situ packages from a document directory."""

from __future__ import annotations

import hashlib
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from situlearn.document import DocumentValidationError, parse_document, raise_for_errors

MAX_ENTRIES = 10_000
MAX_ENTRY_BYTES = 512 * 1024 * 1024
MAX_TOTAL_BYTES = 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 1_000


class PackageError(RuntimeError):
    """A .situ package could not be produced."""

    def __init__(self, message: str, *, code: str = "package/error") -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class PackageInfo:
    path: Path
    entries: tuple[str, ...]
    media_bytes: int
    warnings: tuple[str, ...]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data)


def package_directory(
    source: Path,
    destination: Path,
    *,
    force: bool = False,
) -> PackageInfo:
    """Package ``document.json`` plus its referenced media into a .situ zip."""

    source = source.resolve()
    destination = destination.resolve()
    document_path = source / "document.json"
    if not document_path.is_file():
        raise PackageError(f"missing document.json in {source}", code="document/missing-document")
    if destination.exists() and not force:
        raise PackageError(f"output already exists: {destination}", code="package/output-exists")
    if destination.is_relative_to(source):
        raise PackageError("output must not be inside the source directory", code="package/output-inside-source")

    try:
        document, issues = parse_document(document_path.read_text(encoding="utf-8"), mode="write")
        raise_for_errors(issues)
    except (ValidationError, DocumentValidationError, ValueError) as exc:
        raise PackageError(f"invalid document: {exc}", code="document/malformed-document") from exc

    entries: dict[str, bytes] = {}
    for resource_id, resource in sorted(document.resources.items()):
        raw_path = source / resource.href
        if raw_path.is_symlink():
            raise PackageError(
                f"resource {resource_id!r} is a symlink",
                code="document/unsafe-package-path",
            )
        path = raw_path.resolve()
        if not path.is_relative_to(source):
            raise PackageError(
                f"resource {resource_id!r} escapes the source directory",
                code="document/unsafe-package-path",
            )
        if not path.is_file():
            raise PackageError(
                f"missing resource file: {resource.href}",
                code="document/missing-resource",
            )
        data = path.read_bytes()
        if len(data) > MAX_ENTRY_BYTES:
            raise PackageError(
                f"resource {resource_id!r} exceeds {MAX_ENTRY_BYTES} bytes",
                code="document/limit-exceeded",
            )
        if _sha256(data) != resource.sha256:
            raise PackageError(
                f"resource {resource_id!r} does not match its sha256",
                code="document/hash-mismatch",
            )
        entries[resource.href] = data

    allowed = {"document.json", *entries}
    warnings: list[str] = []
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source).as_posix()
        if relative not in allowed:
            warnings.append(f"skipped unreferenced file: {relative}")

    if len(entries) + 1 > MAX_ENTRIES:
        raise PackageError(f"package exceeds {MAX_ENTRIES} entries", code="document/limit-exceeded")
    media_bytes = sum(len(data) for data in entries.values())
    if media_bytes > MAX_TOTAL_BYTES:
        raise PackageError(
            f"package exceeds {MAX_TOTAL_BYTES} uncompressed bytes",
            code="document/limit-exceeded",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    try:
        with zipfile.ZipFile(
            temporary,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            _write_entry(archive, "document.json", document_path.read_bytes())
            for href in sorted(entries):
                _write_entry(archive, href, entries[href])
        with zipfile.ZipFile(temporary) as archive:
            infos = archive.infolist()
            uncompressed = sum(info.file_size for info in infos)
            compressed = sum(info.compress_size for info in infos)
            if uncompressed > MAX_TOTAL_BYTES:
                raise PackageError(
                    f"package exceeds {MAX_TOTAL_BYTES} uncompressed bytes",
                    code="document/limit-exceeded",
                )
            if compressed and uncompressed / compressed > MAX_COMPRESSION_RATIO:
                raise PackageError(
                    f"package compression ratio exceeds {MAX_COMPRESSION_RATIO}:1",
                    code="document/limit-exceeded",
                )
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return PackageInfo(
        path=destination,
        entries=tuple(sorted(allowed)),
        media_bytes=media_bytes,
        warnings=tuple(warnings),
    )


__all__ = [
    "MAX_COMPRESSION_RATIO",
    "MAX_ENTRIES",
    "MAX_ENTRY_BYTES",
    "MAX_TOTAL_BYTES",
    "PackageError",
    "PackageInfo",
    "package_directory",
]
