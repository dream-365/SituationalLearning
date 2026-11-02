"""Publish and lifecycle API for SituLearn reports."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from situlearn.web.auth import hash_client_ip, require_publish_token
from situlearn.web.config import Settings
from situlearn.web.observability import get_request_id
from situlearn.web.repository import (
    PublishConflict,
    ReportRecord,
    ReportRepository,
    report_id_for,
)
from situlearn.web.storage import (
    PublishValidationError,
    ReportStore,
)

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_publish_token)])

_VALIDATION_STATUS = {
    "ERR_PUBLISH_PAYLOAD_TOO_LARGE": 413,
    "ERR_PUBLISH_INVALID_ARCHIVE": 400,
    "ERR_PUBLISH_MANIFEST_INVALID": 422,
    "ERR_PUBLISH_SCHEMA_UNSUPPORTED": 422,
    "ERR_PUBLISH_ASSET_MISSING": 422,
    "ERR_PUBLISH_CONFLICT": 409,
    "ERR_PUBLISH_STORAGE_FULL": 507,
}


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _repository(request: Request) -> ReportRepository:
    return request.app.state.repository


def _store(request: Request) -> ReportStore:
    return request.app.state.store


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def _validation_error(exc: PublishValidationError) -> HTTPException:
    return _error(
        _VALIDATION_STATUS.get(exc.code, 400),
        exc.code,
        str(exc),
    )


def _new_version() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


async def _save_upload(upload: UploadFile, settings: Settings) -> Path:
    settings.ensure_directories()
    path = settings.staging_dir / f"upload-{uuid.uuid4().hex}.tar.gz"
    total = 0
    try:
        with path.open("wb") as handle:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_report_bytes:
                    raise PublishValidationError(
                        "ERR_PUBLISH_PAYLOAD_TOO_LARGE",
                        f"archive exceeds {settings.max_report_bytes} bytes",
                    )
                handle.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def _report_json(record: ReportRecord, settings: Settings) -> dict[str, object]:
    return {
        "slug": record.slug,
        "url": f"{settings.site_base_url}/r/{record.slug}",
        "report_id": record.report_id,
        "title": record.title,
        "status": record.status,
        "version": record.current_version,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "size_bytes": record.size_bytes,
        "manifest_schema_version": record.manifest_schema_version,
    }


@router.post("/reports")
async def publish_report(
    request: Request,
    archive: Annotated[UploadFile, File()],
    report_key: Annotated[str, Form()],
    schema_version: Annotated[str, Form()],
) -> JSONResponse:
    settings = _settings(request)
    repository = _repository(request)
    store = _store(request)
    request_id = get_request_id()
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hash_client_ip(client_ip, settings.publish_token)

    allowed, retry_after = request.app.state.publish_limiter.allow(client_ip)
    if not allowed:
        request.app.state.metrics.record_publish("rejected")
        raise HTTPException(
            status_code=429,
            detail={
                "code": "ERR_RATE_LIMITED",
                "message": "too many publish attempts",
            },
            headers={"Retry-After": str(retry_after)},
        )

    if not re.fullmatch(r"[0-9a-f]{64}", report_key):
        request.app.state.metrics.record_publish("rejected")
        raise _error(
            422,
            "ERR_PUBLISH_MANIFEST_INVALID",
            "report_key must be 64 lowercase hexadecimal characters",
        )
    if not schema_version or schema_version.split(".", 1)[0] != "1":
        request.app.state.metrics.record_publish("rejected")
        raise _error(
            422,
            "ERR_PUBLISH_SCHEMA_UNSUPPORTED",
            f"unsupported schema version: {schema_version}",
        )

    existing = repository.get_by_key(report_key)
    expected_version = existing.current_version if existing else None
    report_id = existing.report_id if existing else report_id_for(report_key)
    archive_path: Path | None = None
    try:
        archive_path = await _save_upload(archive, settings)
        staged = store.stage(archive_path, report_key=report_key)
    except PublishValidationError as exc:
        request.app.state.metrics.record_publish("rejected")
        repository.record_event(
            report_id=existing.report_id if existing else None,
            request_id=request_id,
            action="publish",
            result="rejected",
            client_ip_hash=ip_hash,
            error_code=exc.code,
        )
        raise _validation_error(exc) from exc
    finally:
        if archive_path is not None:
            archive_path.unlink(missing_ok=True)

    version = _new_version()
    try:
        installed = store.install(staged, report_id=report_id, version=version)
    except PublishValidationError as exc:
        store.abort(staged)
        request.app.state.metrics.record_publish("rejected")
        repository.record_event(
            report_id=existing.report_id if existing else None,
            request_id=request_id,
            action="publish",
            result="rejected",
            client_ip_hash=ip_hash,
            error_code=exc.code,
        )
        raise _validation_error(exc) from exc

    try:
        record = repository.finish_publish(
            report_key=report_key,
            title=staged.title,
            version=version,
            dir_path=installed.dir_path,
            manifest_sha256=staged.manifest_sha256,
            size_bytes=staged.size_bytes,
            schema_version=staged.schema_version,
            expected_current_version=expected_version,
            request_id=request_id,
            client_ip_hash=ip_hash,
        )
    except PublishConflict as exc:
        store.remove_version(report_id, version)
        request.app.state.metrics.record_publish("rejected")
        repository.record_event(
            report_id=existing.report_id if existing else None,
            request_id=request_id,
            action="publish",
            result="rejected",
            client_ip_hash=ip_hash,
            error_code="ERR_PUBLISH_CONFLICT",
        )
        raise _error(409, "ERR_PUBLISH_CONFLICT", str(exc)) from exc
    except Exception as exc:
        store.remove_version(report_id, version)
        request.app.state.metrics.record_publish("failed")
        repository.record_event(
            report_id=existing.report_id if existing else None,
            request_id=request_id,
            action="publish",
            result="failed",
            client_ip_hash=ip_hash,
            error_code="ERR_PUBLISH_DB_BUSY",
        )
        raise _error(503, "ERR_PUBLISH_DB_BUSY", str(exc)) from exc

    request.app.state.metrics.record_publish("success")
    return JSONResponse(
        status_code=201 if existing is None else 200,
        content={
            **_report_json(record, settings),
            "replaced": existing is not None,
        },
    )


@router.delete("/reports/{slug}", status_code=204)
async def unpublish_report(slug: str, request: Request) -> Response:
    repository = _repository(request)
    client_ip = request.client.host if request.client else "unknown"
    record = repository.unpublish(
        slug,
        request_id=get_request_id(),
        client_ip_hash=hash_client_ip(client_ip, _settings(request).publish_token),
    )
    if record is None:
        raise _error(404, "ERR_REPORT_NOT_FOUND", f"unknown report: {slug}")
    return Response(status_code=204)


@router.get("/reports/{slug}")
async def get_report(slug: str, request: Request) -> dict[str, object]:
    repository = _repository(request)
    record = repository.get_by_slug(slug, include_unpublished=True)
    if record is None:
        raise _error(404, "ERR_REPORT_NOT_FOUND", f"unknown report: {slug}")
    return _report_json(record, _settings(request))
