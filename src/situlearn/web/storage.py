"""Immutable report storage and publish archive validation."""

from __future__ import annotations

import contextlib
import hashlib
import json
import shutil
import tarfile
import threading
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from situlearn.web.config import Settings
from situlearn.web.objectstore import (
    ObjectNotFound,
    ObjectStore,
    build_object_store,
)

_SHARED_WITH_MACOS = {".DS_Store"}


def _ignored_member(path: PurePosixPath) -> bool:
    name = path.name
    return (
        name in _SHARED_WITH_MACOS
        or name.startswith("._")
        or path.parts[:1] == ("__MACOSX",)
    )


class PublishValidationError(ValueError):
    """A publish archive failed validation before it could be installed."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StagedReport:
    """A validated report archive extracted into the staging directory."""

    upload_id: str
    root: Path
    report_key: str
    title: str
    schema_version: str
    manifest: dict[str, object]
    size_bytes: int
    manifest_sha256: str


@dataclass(frozen=True)
class VersionRef:
    """A report version that has been installed into immutable storage."""

    report_id: str
    version: str
    object_prefix: str


def _safe_member_path(name: str) -> PurePosixPath:
    if not name or name.startswith("/") or "\\" in name:
        raise PublishValidationError(
            "ERR_PUBLISH_INVALID_ARCHIVE", f"unsafe archive path: {name!r}"
        )
    path = PurePosixPath(name)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise PublishValidationError(
            "ERR_PUBLISH_INVALID_ARCHIVE", f"unsafe archive path: {name!r}"
        )
    return path


def _check_archive_members(
    members: list[tarfile.TarInfo], settings: Settings
) -> dict[str, tarfile.TarInfo]:
    files: dict[str, tarfile.TarInfo] = {}
    total_size = 0
    for member in members:
        path = _safe_member_path(member.name)
        if _ignored_member(path):
            continue
        key = str(path)
        if key in files:
            raise PublishValidationError(
                "ERR_PUBLISH_INVALID_ARCHIVE", f"duplicate archive path: {key!r}"
            )
        if member.isdir():
            files[key] = member
            continue
        if not member.isfile():
            raise PublishValidationError(
                "ERR_PUBLISH_INVALID_ARCHIVE",
                f"unsupported archive member type: {member.name!r}",
            )
        files[key] = member
        total_size += member.size
        if len(files) > settings.max_report_files:
            raise PublishValidationError(
                "ERR_PUBLISH_PAYLOAD_TOO_LARGE",
                f"archive contains more than {settings.max_report_files} files",
            )
        if total_size > settings.max_report_bytes:
            raise PublishValidationError(
                "ERR_PUBLISH_PAYLOAD_TOO_LARGE",
                f"archive exceeds {settings.max_report_bytes} bytes",
            )
    if "manifest.json" not in files:
        raise PublishValidationError(
            "ERR_PUBLISH_MANIFEST_INVALID", "manifest.json is missing from archive root"
        )
    return files


def _extract_members(
    archive: tarfile.TarFile, members: list[tarfile.TarInfo], destination: Path
) -> None:
    for member in members:
        path = _safe_member_path(member.name)
        if _ignored_member(path):
            continue
        target = destination.joinpath(*path.parts)
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source = archive.extractfile(member)
        if source is None:
            raise PublishValidationError(
                "ERR_PUBLISH_INVALID_ARCHIVE", f"cannot read archive member: {member.name!r}"
            )
        with source, target.open("wb") as handle:
            shutil.copyfileobj(source, handle)


def _read_manifest(root: Path) -> tuple[dict[str, object], str]:
    manifest_path = root / "manifest.json"
    try:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise PublishValidationError(
            "ERR_PUBLISH_MANIFEST_INVALID", f"manifest.json is not valid JSON: {exc}"
        ) from exc
    if not isinstance(manifest, dict):
        raise PublishValidationError(
            "ERR_PUBLISH_MANIFEST_INVALID", "manifest.json must contain a JSON object"
        )
    return manifest, hashlib.sha256(raw).hexdigest()


def _validate_manifest(
    manifest: dict[str, object], report_key: str, root: Path
) -> tuple[str, str]:
    schema_version = manifest.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise PublishValidationError(
            "ERR_PUBLISH_MANIFEST_INVALID", "schema_version is missing"
        )
    if schema_version.split(".", 1)[0] != "1":
        raise PublishValidationError(
            "ERR_PUBLISH_SCHEMA_UNSUPPORTED",
            f"unsupported manifest schema version: {schema_version}",
        )

    source = manifest.get("source")
    if not isinstance(source, dict):
        raise PublishValidationError(
            "ERR_PUBLISH_MANIFEST_INVALID", "source metadata is missing"
        )
    source_sha = source.get("sha256")
    if not isinstance(source_sha, str) or source_sha != report_key:
        raise PublishValidationError(
            "ERR_PUBLISH_MANIFEST_INVALID",
            "report_key must equal manifest.source.sha256",
        )

    narrative = manifest.get("narrative")
    if not isinstance(narrative, dict):
        raise PublishValidationError(
            "ERR_PUBLISH_MANIFEST_INVALID", "narrative metadata is missing"
        )
    title = narrative.get("title")
    if not isinstance(title, str) or not title.strip():
        title = "report"

    references: list[str] = []
    assets = manifest.get("assets", [])
    if isinstance(assets, list):
        for asset in assets:
            if isinstance(asset, dict) and isinstance(asset.get("path"), str):
                references.append(asset["path"])
    sections = narrative.get("sections", [])
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, dict):
                continue
            refs = section.get("audio_refs", [])
            if isinstance(refs, list):
                references.extend(ref for ref in refs if isinstance(ref, str))
    terms = manifest.get("terms", [])
    if isinstance(terms, list):
        for term in terms:
            if isinstance(term, dict) and isinstance(term.get("audio_ref"), str):
                references.append(term["audio_ref"])

    for reference in references:
        if not reference or reference == "unavailable":
            continue
        path = _safe_member_path(reference)
        target = root.joinpath(*path.parts)
        if not target.is_file() or target.stat().st_size == 0:
            raise PublishValidationError(
                "ERR_PUBLISH_ASSET_MISSING", f"referenced asset is missing: {reference}"
            )
    return title, schema_version


def _directory_size(root: Path) -> int:
    return sum(path.stat().st_size for path in root.rglob("*") if path.is_file())


class ReportStore:
    """Stage local uploads, validate them, then install immutable objects."""

    def __init__(
        self, settings: Settings, object_store: ObjectStore | None = None
    ) -> None:
        self.settings = settings
        self.objects = object_store or build_object_store(settings)
        self._manifest_cache: dict[str, tuple[float, bytes]] = {}
        self._cache_lock = threading.Lock()

    def _version_prefix(self, report_id: str, version: str) -> str:
        return f"{self.settings.object_prefix}reports/{report_id}/versions/{version}/"

    def _asset_key(self, object_prefix: str, asset_path: str) -> str:
        path = PurePosixPath(asset_path)
        if not asset_path or asset_path.startswith("/") or "\\" in asset_path:
            raise ValueError(f"unsafe asset path: {asset_path!r}")
        if any(part in {"", ".", ".."} for part in path.parts):
            raise ValueError(f"unsafe asset path: {asset_path!r}")
        return f"{object_prefix}assets/{path.as_posix()}"

    def stage(self, archive_path: Path, *, report_key: str) -> StagedReport:
        self.settings.ensure_directories()
        upload_id = uuid.uuid4().hex
        staging_root = self.settings.staging_dir / upload_id
        staging_root.mkdir(parents=True, exist_ok=False)
        try:
            try:
                with tarfile.open(archive_path, "r:gz") as archive:
                    members = archive.getmembers()
                    _check_archive_members(members, self.settings)
                    _extract_members(archive, members, staging_root)
            except (tarfile.TarError, OSError) as exc:
                raise PublishValidationError(
                    "ERR_PUBLISH_INVALID_ARCHIVE", f"cannot read archive: {exc}"
                ) from exc

            manifest, manifest_sha256 = _read_manifest(staging_root)
            title, schema_version = _validate_manifest(manifest, report_key, staging_root)
            return StagedReport(
                upload_id=upload_id,
                root=staging_root,
                report_key=report_key,
                title=title,
                schema_version=schema_version,
                manifest=manifest,
                size_bytes=_directory_size(staging_root),
                manifest_sha256=manifest_sha256,
            )
        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise

    def install(
        self, staged: StagedReport, *, report_id: str, version: str
    ) -> VersionRef:
        prefix = self._version_prefix(report_id, version)
        if next(self.objects.list_keys(prefix), None) is not None:
            raise PublishValidationError(
                "ERR_PUBLISH_CONFLICT", f"version already exists: {version}"
            )
        try:
            for path in sorted(staged.root.rglob("*")):
                if not path.is_file():
                    continue
                relative = path.relative_to(staged.root)
                if _ignored_member(PurePosixPath(relative.as_posix())):
                    continue
                self.objects.put_file(f"{prefix}{relative.as_posix()}", path)
        except Exception:
            with contextlib.suppress(Exception):
                self.objects.delete_prefix(prefix)
            raise
        shutil.rmtree(staged.root, ignore_errors=True)
        return VersionRef(report_id=report_id, version=version, object_prefix=prefix)

    def abort(self, staged: StagedReport) -> None:
        shutil.rmtree(staged.root, ignore_errors=True)

    def remove_version(self, report_id: str, version: str) -> None:
        prefix = self._version_prefix(report_id, version)
        self.objects.delete_prefix(prefix)
        with self._cache_lock:
            self._manifest_cache.pop(prefix, None)

    def read_manifest(self, object_prefix: str) -> bytes:
        if not object_prefix:
            raise ObjectNotFound("version has no object prefix")
        now = time.monotonic()
        with self._cache_lock:
            cached = self._manifest_cache.get(object_prefix)
        if cached is not None and now - cached[0] < self.settings.oss_read_cache_ttl_s:
            return cached[1]
        data = self.objects.get_bytes(f"{object_prefix}manifest.json")
        with self._cache_lock:
            self._manifest_cache[object_prefix] = (now, data)
        return data

    def asset_size(self, object_prefix: str, asset_path: str) -> int:
        return self.objects.stat(self._asset_key(object_prefix, asset_path))

    def read_asset_range(
        self, object_prefix: str, asset_path: str, start: int, end: int
    ) -> Iterator[bytes]:
        key = self._asset_key(object_prefix, asset_path)
        return self.objects.read_range(key, start, end)

    def healthcheck(self) -> None:
        self.objects.healthcheck()
