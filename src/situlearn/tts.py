"""Xiaomi MiMo TTS adapter and text chunking."""

from __future__ import annotations

import base64
import os
import re
import time

import httpx

from situlearn.ratelimit import backoff_delay


class TTSError(RuntimeError):
    """Raised when the TTS provider cannot return usable audio."""


DEFAULT_STYLE = "用自然、清晰、适合纪录片解说的语气，语速适中。"
DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.5-tts"
DEFAULT_VOICE = "冰糖"


def chunk_text(text: str, max_chars: int = 3_000) -> list[str]:
    """Split text at sentence boundaries into chunks no longer than max_chars.

    Whitespace at sentence boundaries may be normalized.
    """

    if max_chars < 1:
        raise ValueError("max_chars must be positive")
    if not text.strip():
        return []
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r"(?<=[。！？.!?])\s*", text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if not sentence:
            continue
        if len(current) + len(sentence) <= max_chars:
            current += sentence
            continue
        if current:
            chunks.append(current)
        current = sentence
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max_chars:]

    if current:
        chunks.append(current)
    return chunks


class XiaomiTTS:
    """Call Xiaomi MiMo TTS through its Chat Completions-compatible endpoint."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = (
            base_url or os.environ.get("MIMO_BASE_URL") or DEFAULT_BASE_URL
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("MIMO_API_KEY")
        if not self.api_key:
            raise TTSError("MIMO_API_KEY is not set")
        self.model = model
        self.timeout_s = timeout_s

    def synthesize(
        self,
        text: str,
        *,
        voice: str = DEFAULT_VOICE,
        fmt: str = "mp3",
        style: str = DEFAULT_STYLE,
    ) -> bytes:
        if not text.strip():
            raise TTSError("text is empty")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": style},
                {"role": "assistant", "content": text},
            ],
            "audio": {"voice": voice, "format": fmt},
            "stream": False,
        }

        data = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=self.timeout_s) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"api-key": self.api_key, "Content-Type": "application/json"},
                        json=payload,
                    )
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt == 2:
                        raise TTSError(f"TTS HTTP {response.status_code}")
                    time.sleep(
                        backoff_delay(
                            attempt,
                            retry_after=response.headers.get("retry-after"),
                        )
                    )
                    continue
                if response.status_code >= 400:
                    raise TTSError(f"TTS HTTP {response.status_code}")
                data = response.json()
                break
            except httpx.HTTPError as exc:
                if attempt == 2:
                    raise TTSError(f"TTS request failed: {exc}") from exc
                time.sleep(backoff_delay(attempt))

        if data is None:
            raise TTSError("TTS request failed after retries")

        try:
            audio_b64 = data["choices"][0]["message"]["audio"]["data"]
            return base64.b64decode(audio_b64)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise TTSError("TTS response did not contain decodable audio.data") from exc
