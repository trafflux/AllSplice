from __future__ import annotations

import contextlib
import time
import uuid
from typing import Any

from ai_gateway.schemas.openai_chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)


class CustomProcessingProvider:
    """Deterministic mock provider that returns OpenAI-compatible responses.

    This provider performs no external calls and produces a stable, typed response suitable for
    early integration and contract testing. It must not log or leak sensitive content.
    """

    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:
        """Create a deterministic chat completion response."""
        created = int(time.time())
        completion_id = f"chatcmpl-{uuid.uuid4().hex}"

        # Minimal, non-sensitive logging placeholder (to be replaced in Phase 10 logging module).
        # Avoid logging message contents or secrets. Only log safe meta.
        _log_info(
            "custom_provider.request",
            {
                "model": req.model,
                "n_messages": len(req.messages),
                "created": created,
            },
        )

        # Deterministic content; echo model only, do not reflect user inputs (to avoid leakage).
        message = ChatMessage(
            role="assistant", content=f"Hello from CustomProcessingProvider ({req.model})."
        )
        choice = Choice(index=0, message=message, finish_reason="stop")

        # Usage not available for mock; provide zeros with a TODO note for future estimation.
        usage = Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

        resp = ChatCompletionResponse(
            id=completion_id,
            object="chat.completion",
            created=created,
            model=req.model,
            choices=[choice],
            usage=usage,
        )

        _log_info(
            "custom_provider.response",
            {
                "id": completion_id,
                "object": "chat.completion",
                "created": created,
                "choices": 1,
            },
        )

        return resp


def _log_info(event: str, fields: dict[str, Any]) -> None:
    """Temporary lightweight structured log.

    Replaced in Phase 10 with centralized logging setup. Avoid secrets.
    """
    with contextlib.suppress(Exception):
        # Keeping it simple; tests don't assert logs. Print allowed per project test rules.
        # In production logging, this will be swapped to a proper logger.
        print(f"{event} {fields}")  # noqa: T201
        # Swallow logging errors to avoid impacting request flow.
        pass
