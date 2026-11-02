from __future__ import annotations

import pytest

from situlearn.tts import TTSError, XiaomiTTS, chunk_text


def test_chunk_text_returns_single_chunk_when_short() -> None:
    assert chunk_text("短句。", max_chars=100) == ["短句。"]


def test_chunk_text_respects_limit_and_preserves_content() -> None:
    text = "第一句。" * 10 + "第二句。" * 10
    chunks = chunk_text(text, max_chars=20)

    assert all(len(chunk) <= 20 for chunk in chunks)
    assert "".join(chunks) == text


def test_chunk_text_handles_empty_text() -> None:
    assert chunk_text("", max_chars=100) == []


def test_tts_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MIMO_API_KEY", raising=False)

    with pytest.raises(TTSError):
        XiaomiTTS(api_key=None)
