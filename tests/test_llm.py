from __future__ import annotations

import pytest

from situlearn.llm import LLMConfigError, make_chat_model


def test_make_chat_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(LLMConfigError):
        make_chat_model()
