"""FastAPI application factory for the SituLearn publishing service."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.responses import Response
from starlette.staticfiles import StaticFiles

from situlearn import __version__
from situlearn.web.api import router as api_router
from situlearn.web.auth import SlidingWindowLimiter
from situlearn.web.config import Settings
from situlearn.web.metrics import Metrics
from situlearn.web.observability import (
    configure_logging,
    reset_request_id,
    set_request_id,
)
from situlearn.web.pwa import manifest_for, offline_html
from situlearn.web.render import (
    PublicReport,
    ReportGone,
    ReportNotFound,
    SectionNotFound,
    load_public_report,
    render_chapter,
    render_report,
    render_vocabulary,
)
from situlearn.web.repository import ReportRepository
from situlearn.web.storage import ReportStore

logger = logging.getLogger("situlearn.web")


def _valid_request_id(value: str | None) -> str | None:
    if not value or not 1 <= len(value) <= 128:
        return None
    if not all(character.isalnum() or character in "-_" for character in value):
        return None
    return value


def _publish_limit(value: str) -> int:
    try:
        return max(1, int(value.split("/", 1)[0]))
    except (AttributeError, ValueError):
        return 5


def _public_report(request: Request, slug: str) -> PublicReport:
    try:
        return load_public_report(
            request.app.state.store,
            request.app.state.repository,
            slug,
        )
    except ReportGone as exc:
        raise HTTPException(
            status_code=410,
            detail={
                "code": "ERR_REPORT_GONE",
                "message": "this report is no longer published",
            },
        ) from exc
    except ReportNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "ERR_REPORT_NOT_FOUND",
                "message": f"unknown report: {slug}",
            },
        ) from exc


def readiness_checks(settings: Settings) -> dict[str, str]:
    """Return the per-dependency readiness result."""

    checks: dict[str, str] = {}
    try:
        settings.ensure_directories()
        with tempfile.NamedTemporaryFile(
            dir=settings.data_dir, prefix=".ready-", delete=True
        ) as handle:
            handle.write(b"ok")
            handle.flush()
        checks["data_dir"] = "ok"
    except OSError as exc:
        checks["data_dir"] = f"error: {exc}"
    return checks


def create_app(settings: Settings | None = None, *, configure_logs: bool = True) -> FastAPI:
    resolved = settings or Settings.from_env()
    if configure_logs:
        configure_logging(resolved.log_level)

    app = FastAPI(
        title="SituLearn",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved
    app.state.metrics = Metrics()
    app.state.store = ReportStore(resolved)
    app.state.repository = ReportRepository(
        resolved.db_path, busy_timeout_ms=resolved.db_busy_timeout_ms
    )
    try:
        resolved.ensure_directories()
        app.state.repository.initialize()
    except OSError:
        # /readyz reports the broken data directory; API calls will fail with 503.
        pass
    app.state.publish_limiter = SlidingWindowLimiter(
        limit=_publish_limit(resolved.publish_rate_limit),
        window_seconds=60.0,
    )
    app.include_router(api_router)
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.middleware("http")
    async def request_context(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _valid_request_id(request.headers.get("X-Request-ID")) or uuid.uuid4().hex
        token = set_request_id(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
            if request.url.path.startswith("/r/") or request.url.path == "/offline":
                response.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("text/html"):
                    response.headers.setdefault(
                        "Content-Security-Policy",
                        "default-src 'self'; media-src 'self'; img-src 'self' data:; "
                        "style-src 'self' 'unsafe-inline'; script-src 'self'; "
                        "connect-src 'self'",
                    )
            return response
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "route": request.url.path,
                    "status": status_code,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started) * 1_000, 2)
            app.state.metrics.observe_http(
                request.method, status_code, duration_ms / 1_000
            )
            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "route": request.url.path,
                    "status": status_code,
                    "duration_ms": duration_ms,
                },
            )
            reset_request_id(token)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz(request: Request) -> JSONResponse:
        checks = readiness_checks(request.app.state.settings)
        ready = all(value == "ok" for value in checks.values())
        return JSONResponse(
            status_code=200 if ready else 503,
            content={"status": "ok" if ready else "unready", "checks": checks},
        )

    @app.get("/r/{slug}", response_class=HTMLResponse)
    async def report_home(slug: str, request: Request) -> HTMLResponse:
        return HTMLResponse(render_report(_public_report(request, slug)))

    @app.head("/r/{slug}", response_class=HTMLResponse)
    async def report_home_head(slug: str, request: Request) -> HTMLResponse:
        return HTMLResponse(render_report(_public_report(request, slug)))

    @app.get("/r/{slug}/vocabulary", response_class=HTMLResponse)
    async def vocabulary_page(
        slug: str,
        request: Request,
        section: str | None = None,
        category: str | None = None,
        q: str | None = None,
    ) -> HTMLResponse:
        report = _public_report(request, slug)
        return HTMLResponse(
            render_vocabulary(
                report,
                section_filter=section,
                category_filter=category,
                query=q,
            )
        )

    @app.get("/r/{slug}/chapters/{section_id}", response_class=HTMLResponse)
    async def chapter_page(slug: str, section_id: str, request: Request) -> HTMLResponse:
        report = _public_report(request, slug)
        try:
            return HTMLResponse(render_chapter(report, section_id))
        except SectionNotFound as exc:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ERR_REPORT_NOT_FOUND",
                    "message": f"unknown section: {section_id}",
                },
            ) from exc

    @app.get("/metrics")
    async def metrics_page(request: Request) -> Response:
        try:
            report_count, storage_bytes = request.app.state.repository.stats()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail={"code": "ERR_METRICS_UNAVAILABLE", "message": str(exc)},
            ) from exc
        return Response(
            content=request.app.state.metrics.render(
                report_count=report_count,
                storage_bytes=storage_bytes,
            ),
            media_type="text/plain; version=0.0.4; charset=utf-8",
            headers={"X-Robots-Tag": "noindex, nofollow"},
        )

    @app.get("/offline", response_class=HTMLResponse)
    async def offline_page() -> HTMLResponse:
        return HTMLResponse(offline_html())

    @app.get("/sw.js")
    async def service_worker() -> FileResponse:
        path = os.path.join(os.path.dirname(__file__), "static", "sw.js")
        return FileResponse(
            path,
            media_type="text/javascript",
            headers={
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-cache",
            },
        )

    @app.get("/r/{slug}/manifest.webmanifest")
    async def report_manifest(slug: str, request: Request) -> Response:
        report = _public_report(request, slug)
        return Response(
            content=json.dumps(manifest_for(report), ensure_ascii=False),
            media_type="application/manifest+json",
            headers={"X-Robots-Tag": "noindex, nofollow"},
        )

    @app.get("/r/{slug}/assets/{asset_path:path}")
    async def report_asset(slug: str, asset_path: str, request: Request) -> FileResponse:
        report = _public_report(request, slug)
        asset_root = (report.version_dir / "assets").resolve()
        target = (asset_root / asset_path).resolve()
        if asset_root not in target.parents and target != asset_root:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "ERR_ASSET_PATH_INVALID",
                    "message": "invalid asset path",
                },
            )
        if not target.is_file():
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "ERR_REPORT_NOT_FOUND",
                    "message": f"unknown asset: {asset_path}",
                },
            )
        media_type = "audio/mpeg" if target.suffix.lower() == ".mp3" else None
        return FileResponse(
            target,
            media_type=media_type,
            headers={"Accept-Ranges": "bytes"},
        )

    return app


app = create_app()
