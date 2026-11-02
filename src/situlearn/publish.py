"""Package a built report and upload it to a SituLearn web server."""

from __future__ import annotations

import os
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from situlearn.knowledge import ReportManifest


class PublishError(RuntimeError):
    """A publish failure with a CLI exit code."""

    def __init__(self, code: str, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


@dataclass(frozen=True)
class PublishResult:
    dry_run: bool
    report_key: str
    title: str
    size_bytes: int
    slug: str | None = None
    url: str | None = None
    report_id: str | None = None
    version: str | None = None
    replaced: bool = False


@dataclass(frozen=True)
class _PreparedArchive:
    path: Path
    report_key: str
    title: str
    schema_version: str
    size_bytes: int


def _load_manifest(report_dir: Path) -> ReportManifest:
    manifest_path = report_dir / "manifest.json"
    if not manifest_path.is_file():
        raise PublishError(
            "ERR_LOCAL_MANIFEST",
            f"manifest.json not found in {report_dir}",
            2,
        )
    try:
        return ReportManifest.model_validate_json(
            manifest_path.read_text(encoding="utf-8")
        )
    except Exception as exc:
        raise PublishError(
            "ERR_LOCAL_MANIFEST",
            f"manifest.json is invalid: {exc}",
            2,
        ) from exc


def _iter_references(manifest: ReportManifest) -> list[str]:
    references: list[str] = [asset.path for asset in manifest.assets]
    for section in manifest.narrative.sections:
        references.extend(section.audio_refs)
    for term in manifest.terms:
        references.append(term.audio_ref)
    return references


def _validate_assets(manifest: ReportManifest, report_dir: Path) -> None:
    for reference in _iter_references(manifest):
        if not reference or reference == "unavailable":
            continue
        path = (report_dir / reference).resolve()
        root = report_dir.resolve()
        if root not in path.parents and path != root:
            raise PublishError(
                "ERR_LOCAL_ASSET",
                f"asset path escapes report directory: {reference}",
                2,
            )
        if not path.is_file() or path.stat().st_size == 0:
            raise PublishError(
                "ERR_LOCAL_ASSET",
                f"referenced asset is missing or empty: {reference}",
                2,
            )


def _build_archive(report_dir: Path, manifest: ReportManifest) -> _PreparedArchive:
    with tempfile.NamedTemporaryFile(
        prefix="situlearn-publish-", suffix=".tar.gz", delete=False
    ) as handle:
        archive_path = Path(handle.name)
    try:
        with tarfile.open(archive_path, "w:gz") as archive:
            for path in sorted(report_dir.rglob("*")):
                if not path.is_file() or path.is_symlink():
                    continue
                archive.add(
                    path,
                    arcname=str(path.relative_to(report_dir)),
                    recursive=False,
                )
    except OSError as exc:
        archive_path.unlink(missing_ok=True)
        raise PublishError(
            "ERR_LOCAL_ARCHIVE", f"cannot package report: {exc}", 2
        ) from exc
    return _PreparedArchive(
        path=archive_path,
        report_key=manifest.source.sha256,
        title=manifest.narrative.title,
        schema_version=manifest.schema_version,
        size_bytes=archive_path.stat().st_size,
    )


def _prepare(report_dir: Path) -> _PreparedArchive:
    if not report_dir.is_dir():
        raise PublishError(
            "ERR_LOCAL_REPORT", f"report directory not found: {report_dir}", 2
        )
    manifest = _load_manifest(report_dir)
    _validate_assets(manifest, report_dir)
    return _build_archive(report_dir, manifest)


def _detail(response: httpx.Response) -> tuple[str, str]:
    try:
        body: Any = response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, dict):
        code = str(detail.get("code") or "ERR_PUBLISH_REJECTED")
        message = str(detail.get("message") or detail)
    elif isinstance(detail, str):
        code = "ERR_PUBLISH_REJECTED"
        message = detail
    else:
        code = "ERR_PUBLISH_REJECTED"
        message = response.text[:300] or f"HTTP {response.status_code}"
    return code, message


def _upload(
    archive: _PreparedArchive,
    server: str,
    token: str,
    *,
    transport: httpx.BaseTransport | None,
    timeout: float,
) -> PublishResult:
    url = server.rstrip("/") + "/api/v1/reports"
    data = {
        "report_key": archive.report_key,
        "schema_version": archive.schema_version,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        with (
            httpx.Client(timeout=timeout, transport=transport) as client,
            archive.path.open("rb") as handle,
        ):
            response = client.post(
                url,
                headers=headers,
                data=data,
                files={
                    "archive": (
                        "report.tar.gz",
                        handle,
                        "application/gzip",
                    )
                },
            )
    except httpx.RequestError as exc:
        raise PublishError(
            "ERR_PUBLISH_NETWORK", f"cannot reach publish server: {exc}", 6
        ) from exc

    if response.status_code == 401:
        code, message = _detail(response)
        raise PublishError(code, message, 5)
    if response.status_code not in {200, 201}:
        code, message = _detail(response)
        raise PublishError(code, message, 7)

    try:
        body = response.json()
        slug = str(body["slug"])
        url_value = str(body["url"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PublishError(
            "ERR_PUBLISH_RESPONSE", "server response is missing slug or url", 7
        ) from exc
    return PublishResult(
        dry_run=False,
        report_key=archive.report_key,
        title=archive.title,
        size_bytes=archive.size_bytes,
        slug=slug,
        url=url_value,
        report_id=body.get("report_id"),
        version=body.get("version"),
        replaced=bool(body.get("replaced")),
    )


def publish_report_dir(
    report_dir: Path,
    server: str,
    token: str,
    *,
    dry_run: bool = False,
    transport: httpx.BaseTransport | None = None,
    timeout: float = 600.0,
) -> PublishResult:
    """Validate, package, and upload a report directory."""

    archive = _prepare(report_dir)
    try:
        if dry_run:
            return PublishResult(
                dry_run=True,
                report_key=archive.report_key,
                title=archive.title,
                size_bytes=archive.size_bytes,
            )
        if not token:
            raise PublishError(
                "ERR_PUBLISH_UNAUTHORIZED",
                "publish token is empty; set SITULEARN_PUBLISH_TOKEN",
                5,
            )
        return _upload(
            archive,
            server,
            token,
            transport=transport,
            timeout=timeout,
        )
    finally:
        archive.path.unlink(missing_ok=True)


def token_from_env(name: str) -> str:
    return os.environ.get(name, "")
