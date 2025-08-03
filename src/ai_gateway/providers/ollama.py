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
from ai_gateway.schemas.openai_embeddings import (
    CreateEmbeddingsRequest,
    CreateEmbeddingsResponse,
    EmbeddingItem,
    EmbeddingUsage,
    deterministic_vector,
    normalize_input_to_strings,
)
from ai_gateway.schemas.openai_models import ListResponse, Model, ModelPermission


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

    async def list_models(self) -> ListResponse[Model]:
        """Return deterministic Ollama models."""
        now = int(time.time())
        perm = ModelPermission(
            id=f"perm-{uuid.uuid4().hex}",
            created=now,
            allow_create_engine=False,
            allow_sampling=True,
            allow_logprobs=False,
            allow_search_indices=False,
            allow_view=True,
            allow_fine_tuning=False,
            organization=None,
            group=None,
            is_blocking=False,
        )
        models = [
            Model(
                id="ollama-tiny",
                created=now,
                owned_by="ollama",
                permission=[perm],
                root=None,
                parent=None,
            ),
            Model(
                id="ollama-medium",
                created=now,
                owned_by="ollama",
                permission=[perm],
                root=None,
                parent=None,
            ),
        ]
        return ListResponse[Model](data=models)

    async def create_embeddings(self, req: CreateEmbeddingsRequest) -> CreateEmbeddingsResponse:
        """Create deterministic embeddings (local stub)."""
        items = normalize_input_to_strings(req.input)
        data: list[EmbeddingItem] = []
        for idx, text in enumerate(items):
            vec = deterministic_vector(text, dim=16)
            data.append(EmbeddingItem(embedding=vec, index=idx))
        prompt_tokens = sum(len(s.split()) for s in items)
        usage = EmbeddingUsage(prompt_tokens=prompt_tokens, total_tokens=prompt_tokens)
        return CreateEmbeddingsResponse(object="list", data=data, model=req.model, usage=usage)
