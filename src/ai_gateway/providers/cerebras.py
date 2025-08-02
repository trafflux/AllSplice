from __future__ import annotations

import time
import uuid
from typing import Any

from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.providers.base import ChatProvider
from ai_gateway.providers.cerebras_client import CerebrasClient
from ai_gateway.schemas.openai_chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    FinishReasonEnum,
    Usage,
)


def _gen_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex}"


def _now_epoch() -> int:
    return int(time.time())


def _map_messages(req: ChatCompletionRequest) -> list[dict[str, str]]:
    # Normalize to role/content dicts for the client
    return [{"role": m.role, "content": m.content} for m in req.messages]


def _map_finish_reason(reason: Any) -> FinishReasonEnum:
    # Map upstream reason into our strict enum; default to "stop"
    if isinstance(reason, str) and reason in ("stop", "length", "content_filter", "tool_calls"):
        return reason  # type: ignore[return-value]
    return "stop"


def _map_usage(data: dict[str, Any] | None) -> Usage:
    if not data:
        return Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)
    prompt = int(data.get("prompt_tokens", 0) or 0)
    completion = int(data.get("completion_tokens", 0) or 0)
    total = int(data.get("total_tokens", prompt + completion))
    return Usage(prompt_tokens=prompt, completion_tokens=completion, total_tokens=total)


class CerebrasProvider(ChatProvider):
    """Cerebras chat provider mapping to OpenAI-compatible schema."""

    def __init__(self, client: CerebrasClient | None = None) -> None:
        self._client = client or CerebrasClient()

    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:
        try:
            client_msgs = _map_messages(req)
            # Forward a subset of OpenAI-style params if present
            kwargs: dict[str, Any] = {}
            if req.temperature is not None:
                kwargs["temperature"] = req.temperature
            if req.max_tokens is not None:
                kwargs["max_tokens"] = req.max_tokens

            raw = await self._client.chat(model=req.model, messages=client_msgs, **kwargs)

            # Extract message content
            choices_raw = raw.get("choices") or []
            if not choices_raw:
                raise ProviderError("Upstream provider error")
            first = choices_raw[0]
            message = first.get("message") or {}
            content = str(message.get("content", ""))

            choice = Choice(
                index=0,
                message=ChatMessage(role="assistant", content=content),
                finish_reason=_map_finish_reason(first.get("finish_reason")),
            )

            usage = _map_usage(raw.get("usage"))

            return ChatCompletionResponse(
                id=_gen_id(),
                object="chat.completion",
                created=_now_epoch(),
                model=req.model,
                choices=[choice],
                usage=usage,
            )
        except ProviderError:
            # Already normalized
            raise
        except Exception as err:
            # Normalize any unexpected upstream exception
            raise ProviderError("Upstream provider error") from err
