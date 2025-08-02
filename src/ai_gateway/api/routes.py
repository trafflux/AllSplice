from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, Depends

from ai_gateway.config.constants import (
    CEREBRAS_BASE,
    HEALTHZ,
    OLLAMA_BASE,
    V1_BASE,
)
from ai_gateway.exceptions.errors import ProviderError
from ai_gateway.middleware.auth import auth_bearer
from ai_gateway.providers.cerebras import CerebrasProvider
from ai_gateway.providers.custom import CustomProcessingProvider
from ai_gateway.providers.ollama import OllamaProvider  # Phase 7 provider
from ai_gateway.schemas.openai_chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage as Message,
    Choice,
    Usage,
)

health_router = APIRouter()
v1_router = APIRouter(prefix=V1_BASE)
cerebras_router = APIRouter(prefix=CEREBRAS_BASE)
ollama_router = APIRouter(prefix=OLLAMA_BASE)


@health_router.get(HEALTHZ)
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


def _mock_chat_response(model: str) -> ChatCompletionResponse:
    """Deterministic mock response meeting OpenAI Chat Completions schema."""
    now = int(time.time())
    chat_id = f"chatcmpl-{uuid.uuid4().hex}"
    return ChatCompletionResponse(
        id=chat_id,
        object="chat.completion",
        created=now,
        model=model,
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content="This is a mock response."),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
    )


@v1_router.post("/chat/completions")
async def chat_completions_v1(
    req: ChatCompletionRequest, token: str = Depends(auth_bearer)
) -> ChatCompletionResponse:
    # Use the CustomProcessingProvider to generate a response
    provider = CustomProcessingProvider()
    return await provider.chat_completions(req)


@cerebras_router.post("/chat/completions")
async def chat_completions_cerebras(
    req: ChatCompletionRequest, token: str = Depends(auth_bearer)
) -> ChatCompletionResponse:
    provider = CerebrasProvider()
    try:
        return await provider.chat_completions(req)
    except ProviderError as exc:
        # Re-raise to be handled by global exception handlers as 502 with standardized payload
        raise exc


@ollama_router.post("/chat/completions")
async def chat_completions_ollama(
    req: ChatCompletionRequest, token: str = Depends(auth_bearer)
) -> ChatCompletionResponse:
    provider = OllamaProvider()
    try:
        return await provider.chat_completions(req)
    except ProviderError as exc:
        # Re-raise to be handled by global exception handlers as 502 with standardized payload
        raise exc
