"""TTS caching, rate limiting, and per-section audio generation."""

from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path

from situlearn.knowledge import AudioStatus, NarrativeSection, TermEntry
from situlearn.tts import TTSError, XiaomiTTS, chunk_text


class RateLimiter:
    def __init__(self, rpm: int = 90) -> None:
        self.interval = 60.0 / max(rpm, 1)
        self._last = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delay = self.interval - (now - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()


class AudioCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(text: str, *, model: str, voice: str, fmt: str) -> str:
        payload = f"{model}:{voice}:{fmt}:{text}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def path_for(self, key: str, fmt: str) -> Path:
        return self.root / f"{key}.{fmt}"

    def get(self, key: str, fmt: str) -> Path | None:
        path = self.path_for(key, fmt)
        if path.exists() and path.stat().st_size > 0:
            return path
        return None

    def put(self, key: str, fmt: str, data: bytes) -> Path:
        path = self.path_for(key, fmt)
        path.write_bytes(data)
        return path


def synthesize_text(
    tts: XiaomiTTS,
    cache: AudioCache,
    limiter: RateLimiter,
    text: str,
    *,
    voice: str,
    fmt: str = "mp3",
) -> Path:
    key = cache.key(text, model=tts.model, voice=voice, fmt=fmt)
    cached = cache.get(key, fmt)
    if cached is not None:
        return cached
    limiter.wait()
    data = tts.synthesize(text, voice=voice, fmt=fmt)
    return cache.put(key, fmt, data)


def export_audio(source: Path, assets_dir: Path, name: str) -> str:
    assets_dir.mkdir(parents=True, exist_ok=True)
    destination = assets_dir / f"{name}{source.suffix}"
    if not (destination.exists() and destination.stat().st_size == source.stat().st_size):
        shutil.copyfile(source, destination)
    return f"assets/audio/{destination.name}"


def synthesize_section(
    tts: XiaomiTTS,
    cache: AudioCache,
    limiter: RateLimiter,
    section: NarrativeSection,
    assets_dir: Path,
    *,
    voice: str,
    max_chars: int = 3_000,
    fmt: str = "mp3",
) -> tuple[list[str], AudioStatus]:
    chunks = chunk_text(section.spoken_text, max_chars)
    if not chunks:
        return [], AudioStatus.UNAVAILABLE

    refs: list[str] = []
    for ordinal, chunk in enumerate(chunks, start=1):
        try:
            cached = synthesize_text(tts, cache, limiter, chunk, voice=voice, fmt=fmt)
        except TTSError:
            return refs, AudioStatus.PARTIAL if refs else AudioStatus.UNAVAILABLE
        refs.append(export_audio(cached, assets_dir, f"{section.section_id}-{ordinal:02d}"))

    return refs, AudioStatus.READY


def synthesize_term(
    tts: XiaomiTTS,
    cache: AudioCache,
    limiter: RateLimiter,
    term: TermEntry,
    assets_dir: Path,
    *,
    voice: str,
    fmt: str = "mp3",
) -> str:
    try:
        cached = synthesize_text(tts, cache, limiter, term.term, voice=voice, fmt=fmt)
    except TTSError:
        return "unavailable"
    slug = hashlib.sha256(term.term.casefold().encode("utf-8")).hexdigest()[:12]
    return export_audio(cached, assets_dir, f"term-{slug}")
