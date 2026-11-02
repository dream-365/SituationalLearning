"""Resolve human pronunciation audio from Oxford and Youdao."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import quote

import httpx

from situlearn.ratelimit import IntervalLimiter, backoff_delay

OXFORD_BASE = "https://www.oxfordlearnersdictionaries.com/media/english/us_pron"
YOUDAO_URL = "https://dict.youdao.com/dictvoice"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
MAX_AUDIO_BYTES = 5_242_880
NEGATIVE_TTL_SECONDS = 3_600
STOPWORDS = {
    "the",
    "of",
    "and",
    "with",
    "in",
    "on",
    "for",
    "to",
    "from",
    "a",
    "an",
    "van",
    "der",
    "de",
    "del",
    "della",
    "di",
    "saint",
    "st",
}
ALIASES = {
    "Melencolia": ["melancholia"],
    "Gatamelata": ["Gattamelata"],
    "Renascita": ["rinascita"],
    "Vasari": ["Giorgio Vasari"],
}


@dataclass
class HumanAudio:
    data: bytes
    url: str
    source: str
    entry_url: str
    scope: str
    matched: str


class HumanAudioResolver:
    def __init__(self, *, timeout_s: float = 12.0) -> None:
        self.client = httpx.Client(
            timeout=timeout_s,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            limits=httpx.Limits(max_connections=8),
        )
        self.oxford_limiter = IntervalLimiter(1 / 8)
        self.youdao_limiter = IntervalLimiter(1 / 8)
        self._word_cache: dict[str, HumanAudio] = {}
        self._cache_lock = threading.Lock()

    def close(self) -> None:
        self.client.close()

    def resolve(self, term: str, lemma: str) -> HumanAudio | None:
        for candidate in self._full_candidates(term, lemma):
            hit = self._lookup(candidate)
            if hit is not None:
                scope = "full" if candidate.casefold() in {
                    term.casefold(),
                    lemma.casefold(),
                } else "alias"
                return replace(hit, scope=scope)

        for candidate in self._keyword_candidates(term):
            hit = self._lookup(candidate)
            if hit is not None:
                return replace(hit, scope="keyword")
        return None

    def _lookup(self, word: str) -> HumanAudio | None:
        key = word.casefold().strip()
        with self._cache_lock:
            cached = self._word_cache.get(key)
        if cached is not None:
            return replace(cached)

        hit = self._oxford(word) or self._youdao(word)
        if hit is not None:
            with self._cache_lock:
                self._word_cache[key] = hit
            return replace(hit)
        return None

    def _oxford(self, word: str) -> HumanAudio | None:
        cleaned = word.strip()
        if len(cleaned) < 2:
            return None
        lowered = cleaned.lower()
        for suffix in (1, 2):
            url = (
                f"{OXFORD_BASE}/{lowered[0]}/{lowered[:3]}/{lowered[:5]}/"
                f"{quote(lowered)}__us_{suffix}.mp3"
            )
            self.oxford_limiter.wait()
            response = self._get(url)
            if response is None:
                continue
            return HumanAudio(
                data=response.content,
                url=url,
                source="Oxford Learner's Dictionaries",
                entry_url=f"https://www.oxfordlearnersdictionaries.com/definition/english/{quote(lowered)}",
                scope="full",
                matched=cleaned,
            )
        return None

    def _youdao(self, word: str) -> HumanAudio | None:
        cleaned = word.strip()
        if len(cleaned) < 2:
            return None
        for accent in (1, 2):
            self.youdao_limiter.wait()
            response = self._get(YOUDAO_URL, params={"audio": cleaned, "type": accent})
            if response is None:
                continue
            return HumanAudio(
                data=response.content,
                url=str(response.url),
                source="Youdao Dictionary",
                entry_url=f"https://dict.youdao.com/w/{quote(cleaned)}",
                scope="full",
                matched=cleaned,
            )
        return None

    def _get(self, url: str, params: dict[str, object] | None = None):
        for attempt in range(3):
            try:
                response = self.client.get(url, params=params)
            except httpx.HTTPError:
                time.sleep(backoff_delay(attempt))
                continue
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("audio/") and 1_000 <= len(response.content) <= MAX_AUDIO_BYTES:
                    return response
                return None
            if response.status_code in (429, 500, 502, 503, 504):
                time.sleep(
                    backoff_delay(
                        attempt,
                        retry_after=response.headers.get("retry-after"),
                    )
                )
                continue
            return None
        return None

    @staticmethod
    def _full_candidates(term: str, lemma: str) -> list[str]:
        candidates = [term]
        if lemma.casefold() != term.casefold():
            candidates.append(lemma)
        candidates.extend(ALIASES.get(term, []))
        seen: list[str] = []
        for candidate in candidates:
            if candidate and candidate.casefold() not in {item.casefold() for item in seen}:
                seen.append(candidate)
        return seen

    @staticmethod
    def _keyword_candidates(term: str) -> list[str]:
        words = [
            word.strip(".,'’()-")
            for word in re.findall(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’.-]*", term)
        ]
        words = [
            word
            for word in words
            if len(word) >= 3 and word.casefold() not in STOPWORDS
        ]
        unique: list[str] = []
        for word in words:
            if word.casefold() not in {item.casefold() for item in unique}:
                unique.append(word)
        return sorted(unique, key=lambda word: -len(word))


def _slug(term: str) -> str:
    return hashlib.sha256(term.casefold().encode("utf-8")).hexdigest()[:12]


def resolve_human_audio(
    terms: list[object],
    candidates: list[object],
    *,
    cache_dir: Path,
    cache_path: Path,
    force: bool = False,
    workers: int = 2,
) -> dict[str, HumanAudio | None]:
    """Resolve human audio for every term, caching MP3 bytes and metadata."""

    cache_dir.mkdir(parents=True, exist_ok=True)
    candidate_by_term = {candidate.term.casefold(): candidate for candidate in candidates}
    cached: dict[str, HumanAudio | None] = {}

    if cache_path.exists() and not force:
        metadata = json.loads(cache_path.read_text(encoding="utf-8"))
        for term in terms:
            item = metadata.get(term.term)
            if item is None:
                continue
            if item.get("hit") is False:
                checked_at = float(item.get("checked_at", 0))
                if time.time() - checked_at < NEGATIVE_TTL_SECONDS:
                    cached[term.term] = None
                continue
            audio_path = cache_dir / item["file"]
            if not audio_path.exists():
                continue
            cached[term.term] = HumanAudio(
                data=audio_path.read_bytes(),
                url=item["url"],
                source=item["source"],
                entry_url=item["entry_url"],
                scope=item["scope"],
                matched=item["matched"],
            )

    pending = [term for term in terms if term.term not in cached]
    if pending:
        resolver = HumanAudioResolver()

        def work(term):
            candidate = candidate_by_term.get(term.term.casefold())
            lemma = candidate.lemma if candidate is not None else term.term
            return term.term, resolver.resolve(term.term, lemma)

        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                for term_name, hit in pool.map(work, pending):
                    cached[term_name] = hit
        finally:
            resolver.close()

    metadata: dict[str, object] = {}
    for term in terms:
        hit = cached.get(term.term)
        if hit is None:
            metadata[term.term] = {"hit": False, "checked_at": time.time()}
            continue
        filename = f"{_slug(term.term)}.mp3"
        (cache_dir / filename).write_bytes(hit.data)
        metadata[term.term] = {
            "hit": True,
            "file": filename,
            "url": hit.url,
            "source": hit.source,
            "entry_url": hit.entry_url,
            "scope": hit.scope,
            "matched": hit.matched,
        }

    cache_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return cached
