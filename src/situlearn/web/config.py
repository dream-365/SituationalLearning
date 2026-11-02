"""Runtime configuration for the SituLearn web service."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path


def _env_path(env: Mapping[str, str], name: str, default: Path) -> Path:
    raw = env.get(name)
    return Path(raw).expanduser() if raw else default


def _env_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _env_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or raw == "":
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean")


def _default_data_dir() -> Path:
    return Path.home() / ".cache" / "situlearn" / "web"


def _default_backup_dir() -> Path:
    return Path.home() / ".cache" / "situlearn" / "backup"


@dataclass(frozen=True)
class Settings:
    """All runtime settings, resolved once at process start."""

    data_dir: Path = field(default_factory=_default_data_dir)
    backup_dir: Path = field(default_factory=_default_backup_dir)
    site_base_url: str = "http://localhost:8000"
    publish_token: str = ""
    publish_enabled: bool = True
    max_report_bytes: int = 100 * 1024 * 1024
    max_report_files: int = 2_000
    max_reports: int = 50
    publish_rate_limit: str = "5/min"
    public_rate_limit: str = "120/min/IP"
    previous_version_ttl_h: int = 24
    audio_cache_max_mb: int = 200
    db_busy_timeout_ms: int = 5_000
    log_level: str = "info"
    sentry_dsn: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = os.environ if env is None else env
        return cls(
            data_dir=_env_path(source, "SITULEARN_DATA_DIR", _default_data_dir()),
            backup_dir=_env_path(source, "SITULEARN_BACKUP_DIR", _default_backup_dir()),
            site_base_url=source.get("SITE_BASE_URL", "http://localhost:8000").rstrip("/"),
            publish_token=source.get("PUBLISH_TOKEN", ""),
            publish_enabled=_env_bool(source, "PUBLISH_ENABLED", True),
            max_report_bytes=_env_int(
                source, "MAX_REPORT_BYTES", 100 * 1024 * 1024
            ),
            max_report_files=_env_int(source, "MAX_REPORT_FILES", 2_000),
            max_reports=_env_int(source, "MAX_REPORTS", 50),
            publish_rate_limit=source.get("PUBLISH_RATE_LIMIT", "5/min"),
            public_rate_limit=source.get("PUBLIC_RATE_LIMIT", "120/min/IP"),
            previous_version_ttl_h=_env_int(source, "PREVIOUS_VERSION_TTL_H", 24),
            audio_cache_max_mb=_env_int(source, "AUDIO_CACHE_MAX_MB", 200),
            db_busy_timeout_ms=_env_int(source, "DB_BUSY_TIMEOUT_MS", 5_000),
            log_level=source.get("LOG_LEVEL", "info").lower(),
            sentry_dsn=(source.get("SENTRY_DSN") or None),
        )

    @property
    def db_path(self) -> Path:
        return self.data_dir / "situlearn.sqlite3"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def staging_dir(self) -> Path:
        return self.data_dir / "staging"

    @property
    def trash_dir(self) -> Path:
        return self.data_dir / "trash"

    def ensure_directories(self) -> None:
        for path in (
            self.data_dir,
            self.reports_dir,
            self.staging_dir,
            self.trash_dir,
            self.backup_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
