"""Object storage abstraction for report files.

Production uses Aliyun OSS; tests and local development fall back to a
filesystem-backed store rooted under the data directory.
"""

from __future__ import annotations

import logging
import shutil
import threading
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import NoReturn, Protocol

from situlearn.web.config import Settings

logger = logging.getLogger("situlearn.web")

_CHUNK_SIZE = 64 * 1024

_CONTENT_TYPES = {
    ".json": "application/json",
    ".html": "text/html; charset=utf-8",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".webmanifest": "application/manifest+json",
}


class ObjectStoreError(RuntimeError):
    """The object store is unavailable or rejected a request."""


class ObjectNotFound(ObjectStoreError):
    """The requested object does not exist."""


def content_type_for(path: str | Path) -> str:
    return _CONTENT_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def _safe_key(key: str) -> str:
    path = PurePosixPath(key)
    if not key or key.startswith("/") or "\\" in key:
        raise ValueError(f"unsafe object key: {key!r}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe object key: {key!r}")
    return str(path)


class ObjectStore(Protocol):
    """The subset of object storage the web service needs."""

    prefix: str

    def put_file(self, key: str, path: Path) -> None: ...

    def put_bytes(self, key: str, data: bytes) -> None: ...

    def get_bytes(self, key: str) -> bytes: ...

    def stat(self, key: str) -> int: ...

    def read_range(self, key: str, start: int, end: int) -> Iterator[bytes]: ...

    def delete_key(self, key: str) -> None: ...

    def delete_prefix(self, prefix: str) -> None: ...

    def list_keys(self, prefix: str) -> Iterator[str]: ...

    def healthcheck(self) -> None: ...


class LocalObjectStore:
    """Filesystem-backed store used by tests and local development."""

    def __init__(self, root: Path, *, prefix: str = "") -> None:
        self.root = Path(root)
        self.prefix = prefix

    def _path(self, key: str) -> Path:
        key = _safe_key(key)
        candidate = (self.root / key).resolve()
        root = self.root.resolve()
        if root not in candidate.parents and candidate != root:
            raise ValueError(f"object key escapes store root: {key!r}")
        return candidate

    def put_file(self, key: str, path: Path) -> None:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)

    def put_bytes(self, key: str, data: bytes) -> None:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def get_bytes(self, key: str) -> bytes:
        target = self._path(key)
        try:
            return target.read_bytes()
        except FileNotFoundError as exc:
            raise ObjectNotFound(f"object not found: {key}") from exc

    def stat(self, key: str) -> int:
        target = self._path(key)
        try:
            return target.stat().st_size
        except FileNotFoundError as exc:
            raise ObjectNotFound(f"object not found: {key}") from exc

    def read_range(self, key: str, start: int, end: int) -> Iterator[bytes]:
        target = self._path(key)

        def _iter() -> Iterator[bytes]:
            try:
                handle = target.open("rb")
            except FileNotFoundError as exc:
                raise ObjectNotFound(f"object not found: {key}") from exc
            with handle:
                handle.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = handle.read(min(_CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        return _iter()

    def delete_key(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def delete_prefix(self, prefix: str) -> None:
        root = self.root.resolve()
        target = (self.root / prefix).resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"prefix escapes store root: {prefix!r}")
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        else:
            target.unlink(missing_ok=True)

    def list_keys(self, prefix: str) -> Iterator[str]:
        base = self.root / prefix
        if not base.exists():
            return iter(())
        root = self.root.resolve()
        keys = []
        for path in base.rglob("*"):
            if path.is_file():
                keys.append(path.relative_to(root).as_posix())
        return iter(sorted(keys))

    def healthcheck(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        probe = self.root / ".healthcheck"
        try:
            probe.write_bytes(b"ok")
        finally:
            probe.unlink(missing_ok=True)


class OssObjectStore:
    """Aliyun OSS-backed store. All calls are synchronous."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint: str,
        prefix: str,
        access_key_id: str,
        access_key_secret: str,
        connect_timeout_ms: int = 3_000,
    ) -> None:
        import oss2  # type: ignore[import-untyped]
        from oss2 import exceptions as oss_exceptions  # type: ignore[import-untyped]

        self._oss2 = oss2
        self._exceptions = oss_exceptions
        self.prefix = prefix
        if not endpoint.startswith(("http://", "https://")):
            endpoint = f"https://{endpoint}"
        self._bucket = oss2.Bucket(
            oss2.Auth(access_key_id, access_key_secret),
            endpoint,
            bucket,
            connect_timeout=connect_timeout_ms / 1_000,
        )
        self._lock = threading.Lock()

    def _raise(self, action: str, key: str, exc: Exception) -> NoReturn:
        if isinstance(
            exc,
            (
                self._exceptions.NoSuchKey,
                self._exceptions.NotFound,
            ),
        ):
            raise ObjectNotFound(f"object not found: {key}") from exc
        raise ObjectStoreError(f"OSS {action} failed for {key}: {exc}") from exc

    def put_file(self, key: str, path: Path) -> None:
        key = _safe_key(key)
        try:
            self._bucket.put_object_from_file(
                key, str(path), headers={"Content-Type": content_type_for(path)}
            )
        except Exception as exc:  # noqa: BLE001 - SDK exception hierarchy is broad
            self._raise("put", key, exc)

    def put_bytes(self, key: str, data: bytes) -> None:
        key = _safe_key(key)
        try:
            self._bucket.put_object(
                key, data, headers={"Content-Type": content_type_for(key)}
            )
        except Exception as exc:  # noqa: BLE001
            self._raise("put", key, exc)

    def get_bytes(self, key: str) -> bytes:
        key = _safe_key(key)
        try:
            result = self._bucket.get_object(key)
        except Exception as exc:  # noqa: BLE001
            self._raise("get", key, exc)
        try:
            return result.read()
        finally:
            _close_quietly(result)

    def stat(self, key: str) -> int:
        key = _safe_key(key)
        try:
            return int(self._bucket.head_object(key).content_length)
        except Exception as exc:  # noqa: BLE001
            self._raise("head", key, exc)

    def read_range(self, key: str, start: int, end: int) -> Iterator[bytes]:
        key = _safe_key(key)

        def _iter() -> Iterator[bytes]:
            try:
                result = self._bucket.get_object(key, byte_range=(start, end))
            except Exception as exc:  # noqa: BLE001
                self._raise("get-range", key, exc)
            try:
                while True:
                    chunk = result.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
            finally:
                _close_quietly(result)

        return _iter()

    def delete_key(self, key: str) -> None:
        key = _safe_key(key)
        try:
            self._bucket.delete_object(key)
        except Exception as exc:  # noqa: BLE001
            self._raise("delete", key, exc)

    def delete_prefix(self, prefix: str) -> None:
        try:
            keys: list[str] = []
            for item in self._oss2.ObjectIteratorV2(self._bucket, prefix=prefix):
                keys.append(item.key)
                if len(keys) >= 1_000:
                    self._bucket.batch_delete_objects(keys)
                    keys.clear()
            if keys:
                self._bucket.batch_delete_objects(keys)
        except Exception as exc:  # noqa: BLE001
            self._raise("delete-prefix", prefix, exc)

    def list_keys(self, prefix: str) -> Iterator[str]:
        try:
            for item in self._oss2.ObjectIteratorV2(self._bucket, prefix=prefix):
                yield item.key
        except Exception as exc:  # noqa: BLE001
            self._raise("list", prefix, exc)

    def healthcheck(self) -> None:
        try:
            with self._lock:
                self._bucket.list_objects(prefix=self.prefix, max_keys=1)
        except Exception as exc:  # noqa: BLE001
            self._raise("healthcheck", self.prefix, exc)


def _close_quietly(result: object) -> None:
    close = getattr(result, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            logger.debug("failed to close OSS response", exc_info=True)


def build_object_store(settings: Settings) -> ObjectStore:
    """Return OSS when configured, otherwise a local filesystem store."""

    if settings.oss_bucket or settings.oss_endpoint:
        if not settings.oss_configured:
            raise ObjectStoreError(
                "OSS is partially configured; set OSS_BUCKET, OSS_ENDPOINT, "
                "OSS_ACCESS_KEY_ID and OSS_ACCESS_KEY_SECRET"
            )
        return OssObjectStore(
            bucket=settings.oss_bucket,
            endpoint=settings.oss_endpoint,
            prefix=settings.object_prefix,
            access_key_id=settings.oss_access_key_id,
            access_key_secret=settings.oss_access_key_secret,
            connect_timeout_ms=settings.oss_connect_timeout_ms,
        )
    return LocalObjectStore(
        settings.data_dir / "objects", prefix=settings.object_prefix
    )
