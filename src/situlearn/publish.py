"""Package a SituLearn document and upload it to a web server."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from situlearn.document import Document, parse_document, raise_for_errors
from situlearn.packager import PackageError, package_directory
from situlearn.resolver import PackageResolver


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
    requested_slug: str | None
    size_bytes: int
    cleanup: bool


def _load_document(source: Path) -> Document:
    try:
        if source.is_dir():
            document_path = source / "document.json"
            if not document_path.is_file():
                raise PublishError(
                    "ERR_LOCAL_DOCUMENT",
                    f"document.json not found in {source}",
                    2,
                )
            raw = document_path.read_text(encoding="utf-8")
        elif source.is_file():
            with PackageResolver(source) as package:
                raw = package.read_entry("document.json").decode("utf-8")
        else:
            raise PublishError(
                "ERR_LOCAL_DOCUMENT", f"document source not found: {source}", 2
            )
        document, issues = parse_document(raw, mode="write")
        raise_for_errors(issues)
        return document
    except PublishError:
        raise
    except Exception as exc:
        raise PublishError(
            "ERR_LOCAL_DOCUMENT", f"document is invalid: {exc}", 2
        ) from exc


def _sidecar_slug(source: Path) -> str | None:
    sidecar = source / "publish.json"
    if not sidecar.is_file():
        return None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PublishError(
            "ERR_LOCAL_SIDECAR", f"publish.json is invalid: {exc}", 2
        ) from exc
    slug = payload.get("slug") if isinstance(payload, dict) else None
    return slug if isinstance(slug, str) and slug else None


def _prepare(source: Path, *, slug: str | None) -> _PreparedArchive:
    source = source.expanduser().resolve()
    document = _load_document(source)
    requested_slug = slug or (_sidecar_slug(source) if source.is_dir() else None)
    report_key = (
        document.meta.source.sha256
        if document.meta.source and document.meta.source.sha256
        else document.meta.id
    )
    if not report_key:
        raise PublishError(
            "ERR_LOCAL_DOCUMENT",
            "document needs meta.source.sha256 or meta.id",
            2,
        )

    cleanup = False
    if source.is_dir():
        with tempfile.NamedTemporaryFile(
            prefix="situlearn-publish-", suffix=".situ", delete=False
        ) as handle:
            archive_path = Path(handle.name)
        try:
            package_directory(source, archive_path, force=True)
        except PackageError as exc:
            archive_path.unlink(missing_ok=True)
            raise PublishError(exc.code, str(exc), 2) from exc
        cleanup = True
    else:
        archive_path = source

    return _PreparedArchive(
        path=archive_path,
        report_key=report_key,
        title=document.meta.title,
        requested_slug=requested_slug,
        size_bytes=archive_path.stat().st_size,
        cleanup=cleanup,
    )


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
    data: dict[str, str] = {}
    if archive.requested_slug:
        data["requested_slug"] = archive.requested_slug
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
                        "report.situ",
                        handle,
                        "application/zip",
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


def publish_source(
    source: Path,
    server: str,
    token: str,
    *,
    slug: str | None = None,
    dry_run: bool = False,
    transport: httpx.BaseTransport | None = None,
    timeout: float = 600.0,
) -> PublishResult:
    """Validate, package (if needed), and upload a document directory or .situ."""

    archive = _prepare(source, slug=slug)
    try:
        if dry_run:
            return PublishResult(
                dry_run=True,
                report_key=archive.report_key,
                title=archive.title,
                size_bytes=archive.size_bytes,
                slug=archive.requested_slug,
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
        if archive.cleanup:
            archive.path.unlink(missing_ok=True)


def publish_report_dir(
    report_dir: Path,
    server: str,
    token: str,
    *,
    slug: str | None = None,
    dry_run: bool = False,
    transport: httpx.BaseTransport | None = None,
    timeout: float = 600.0,
) -> PublishResult:
    return publish_source(
        report_dir,
        server,
        token,
        slug=slug,
        dry_run=dry_run,
        transport=transport,
        timeout=timeout,
    )


def token_from_env(name: str) -> str:
    return os.environ.get(name, "")


__all__ = [
    "PublishError",
    "PublishResult",
    "publish_report_dir",
    "publish_source",
    "token_from_env",
]
