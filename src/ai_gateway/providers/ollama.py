from __future__ import annotations

import time
import uuid
from typing import Any

from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.providers.base import ChatProvider
from ai_gateway.providers.ollama_client import OllamaClient
from ai_gateway.schemas.openai_chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)


def _now_epoch() -> int:
    return int(time.time())


def _gen_id() -> str:
    return f"chatcmpl-{uuid.uuid4()}"


class OllamaProvider(ChatProvider):
    """Provider that adapts OpenAI Chat Completions requests to the Ollama API.

    This implementation uses a minimal OllamaClient that currently returns a deterministic
    mock response to keep CI hermetic. The mapping logic is written to be ready for a real
    HTTP client replacement without changing the provider interface.
    """

    def __init__(self, client: OllamaClient | None = None) -> None:
        self._client = client or OllamaClient()

    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:
        # Map OpenAI-style messages to the simplified shape the Ollama client expects
        in_messages: list[dict[str, str]] = [
            {"role": m.role, "content": m.content} for m in req.messages
        ]

        # Call Ollama client (mocked for now)
        try:
            raw: dict[str, Any] = await self._client.chat(model=req.model, messages=in_messages)
        except Exception as exc:
            # Normalize any client/upstream failure into ProviderError (handled as 502)
            raise ProviderError("Upstream provider error") from exc

        # Transform Ollama response to OpenAI-compatible response
        created = _now_epoch()
        completion_id = _gen_id()

        assistant_msg = ChatMessage(
            role="assistant", content=(raw.get("message") or {}).get("content", "")
        )
        choice = Choice(index=0, message=assistant_msg, finish_reason="stop")

        usage = Usage(
            prompt_tokens=0, completion_tokens=0, total_tokens=0
        )  # TODO: refine when available

        return ChatCompletionResponse(
            id=completion_id,
            object="chat.completion",
            created=created,
            model=req.model,
            choices=[choice],
            usage=usage,
        )
