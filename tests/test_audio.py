from __future__ import annotations

import hashlib
from pathlib import Path

from situlearn.audio import AudioCache, synthesize_text


class FakeTTS:
    model = "fake-tts"

    def __init__(self) -> None:
        self.calls = 0
        self.styles: list[str | None] = []

    def synthesize(
        self,
        text: str,
        *,
        voice: str = "冰糖",
        fmt: str = "mp3",
        style: str | None = None,
    ) -> bytes:
        self.calls += 1
        self.styles.append(style)
        return f"audio:{text}:{voice}:{fmt}".encode()


class FakeLimiter:
    def wait(self) -> None:
        return None


def test_audio_cache_key_is_deterministic(tmp_path: Path) -> None:
    cache = AudioCache(tmp_path)
    first = cache.key("hello", model="m", voice="v", fmt="mp3")
    second = cache.key("hello", model="m", voice="v", fmt="mp3")

    assert first == second
    assert len(first) == 64


def test_synthesize_text_uses_cache(tmp_path: Path) -> None:
    tts = FakeTTS()
    cache = AudioCache(tmp_path)
    limiter = FakeLimiter()

    first = synthesize_text(tts, cache, limiter, "hello", voice="冰糖")
    second = synthesize_text(tts, cache, limiter, "hello", voice="冰糖")

    assert first == second
    assert tts.calls == 1
    assert first.read_bytes() == "audio:hello:冰糖:mp3".encode()


def test_audio_cache_key_without_style_matches_legacy_algorithm() -> None:
    expected = hashlib.sha256(b"m:v:mp3:hello").hexdigest()

    assert AudioCache.key("hello", model="m", voice="v", fmt="mp3") == expected
    assert (
        AudioCache.key("hello", model="m", voice="v", fmt="mp3", style=None)
        == expected
    )


def test_audio_cache_key_includes_style() -> None:
    plain = AudioCache.key("hello", model="m", voice="v", fmt="mp3")
    styled = AudioCache.key("hello", model="m", voice="v", fmt="mp3", style="movie")

    assert styled != plain


def test_synthesize_text_passes_style_and_isolates_cache(tmp_path: Path) -> None:
    tts = FakeTTS()
    cache = AudioCache(tmp_path)
    limiter = FakeLimiter()

    documentary = synthesize_text(tts, cache, limiter, "hello", voice="冰糖")
    movie = synthesize_text(
        tts, cache, limiter, "hello", voice="冰糖", style="movie"
    )

    assert documentary != movie
    assert tts.calls == 2
    assert tts.styles == [None, "movie"]
