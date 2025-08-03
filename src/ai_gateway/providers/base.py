from __future__ import annotations

from typing import Protocol, TypeVar

from ai_gateway.schemas.openai_chat import ChatCompletionRequest, ChatCompletionResponse
from ai_gateway.schemas.openai_embeddings import CreateEmbeddingsRequest, CreateEmbeddingsResponse
from ai_gateway.schemas.openai_models import ListResponse, Model

T = TypeVar("T")


class ChatProvider(Protocol):
    """Protocol for chat completion providers.

    Implementations must map from our OpenAI-compatible ChatCompletionRequest to an
    OpenAI-compatible ChatCompletionResponse. All calls are async and must be non-blocking.
    """

    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:
        """Create a chat completion response.

        Args:
            req: OpenAI-compatible chat completion request.

        Returns:
            OpenAI-compatible chat completion response.
        """
        ...

    async def list_models(self) -> ListResponse[Model]:
        """List models available for this provider."""
        ...

    async def create_embeddings(self, req: CreateEmbeddingsRequest) -> CreateEmbeddingsResponse:
        """Create embeddings for the given input."""
        ...
