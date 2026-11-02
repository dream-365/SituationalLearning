"""Free dictionary lookup and audio download."""

from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from situlearn.ratelimit import IntervalLimiter, backoff_delay

DEFAULT_API = "https://api.dictionaryapi.dev/api/v2/entries/en"
DEFAULT_MAX_AUDIO_BYTES = 5_242_880


class DictionaryEntry(BaseModel):
    word: str
    phonetic: str | None = None
    audio_url: str | None = None
    part_of_speech: str = "unknown"
    definition_en: str = ""
    source_url: str


def parse_entry(data: object, term: str) -> DictionaryEntry | None:
    if not isinstance(data, list) or not data:
        return None
    entry = data[0]
    if not isinstance(entry, dict):
        return None

    phonetics = entry.get("phonetics") or []
    phonetic = next(
        (item.get("text") for item in phonetics if isinstance(item, dict) and item.get("text")),
        entry.get("phonetic"),
    )
    audio_url = next(
        (item.get("audio") for item in phonetics if isinstance(item, dict) and item.get("audio")),
        None,
    )

    meanings = entry.get("meanings") or []
    meaning = meanings[0] if meanings and isinstance(meanings[0], dict) else {}
    definitions = meaning.get("definitions") or []
    definition_en = (
        definitions[0].get("definition")
        if definitions and isinstance(definitions[0], dict)
        else ""
    )

    return DictionaryEntry(
        word=str(entry.get("word", term)),
        phonetic=phonetic,
        audio_url=audio_url,
        part_of_speech=str(meaning.get("partOfSpeech", "unknown")),
        definition_en=str(definition_en),
        source_url=f"{DEFAULT_API}/{quote(term)}",
    )


class DictionaryClient:
    def __init__(self, *, timeout_s: float = 5.0, retries: int = 2) -> None:
        self.timeout_s = timeout_s
        self.retries = retries
        self.limiter = IntervalLimiter(0.2)

    def lookup(self, term: str) -> DictionaryEntry | None:
        url = f"{DEFAULT_API}/{quote(term)}"
        for attempt in range(self.retries + 1):
            self.limiter.wait()
            try:
                with httpx.Client(timeout=self.timeout_s) as client:
                    response = client.get(url)
                if response.status_code == 404:
                    return None
                if response.status_code in (429, 500, 502, 503, 504):
                    if attempt == self.retries:
                        return None
                    time.sleep(
                        backoff_delay(
                            attempt,
                            retry_after=response.headers.get("retry-after"),
                        )
                    )
                    continue
                response.raise_for_status()
                return parse_entry(response.json(), term)
            except (httpx.HTTPError, ValueError):
                if attempt == self.retries:
                    return None
                time.sleep(backoff_delay(attempt))
        return None


def download_audio(
    url: str,
    destination: Path,
    *,
    max_bytes: int = DEFAULT_MAX_AUDIO_BYTES,
) -> bool:
    try:
        with (
            httpx.Client(timeout=30.0, follow_redirects=True) as client,
            client.stream("GET", url) as response,
        ):
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("audio/"):
                return False
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    return False
                chunks.append(chunk)
    except httpx.HTTPError:
        return False

    if not chunks:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"".join(chunks))
    return True
