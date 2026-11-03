"""DeepSeek chat model factory."""

from __future__ import annotations

import os
import time
from typing import Any, TypeVar

from langchain_core.exceptions import OutputParserException
from langchain_core.runnables import Runnable
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel, ValidationError

DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

T = TypeVar("T", bound=BaseModel)


class LLMConfigError(RuntimeError):
    """Raised when the DeepSeek client cannot be configured."""


def make_chat_model(
    model: str | None = None, *, max_tokens: int = 64_000
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


def invoke_with_retry(
    chain: Runnable, payload: dict[str, Any], *, attempts: int = 3
) -> Any:
    """Invoke a structured-output chain, retrying malformed model output.

    A truncated or off-schema JSON response should cost one retry, not the
    whole build.
    """

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return chain.invoke(payload)
        except (OutputParserException, ValidationError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(min(2.0 * attempt, 10.0))
    raise last_error  # type: ignore[misc]
