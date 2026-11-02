"""DeepSeek chat model factory."""

from __future__ import annotations

import os
from typing import TypeVar

from langchain_core.runnables import Runnable
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel

DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

T = TypeVar("T", bound=BaseModel)


class LLMConfigError(RuntimeError):
    """Raised when the DeepSeek client cannot be configured."""


def make_chat_model(
    model: str | None = None, *, max_tokens: int = 32_000
) -> ChatDeepSeek:
    """Build a ChatDeepSeek client from environment variables."""

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise LLMConfigError("DEEPSEEK_API_KEY is not set")

    return ChatDeepSeek(
        model=model or os.environ.get("DEEPSEEK_MODEL", DEFAULT_MODEL),
        api_key=api_key,
        api_base=os.environ.get("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL),
        max_tokens=max_tokens,
        max_retries=3,
    )


def structured_output(llm: ChatDeepSeek, schema: type[T]) -> Runnable:
    """Return a runnable that yields validated Pydantic objects.

    deepseek-flash runs in thinking mode, which rejects tool_choice; JSON mode
    plus Pydantic validation is the supported path.
    """

    return llm.with_structured_output(schema, method="json_mode")
