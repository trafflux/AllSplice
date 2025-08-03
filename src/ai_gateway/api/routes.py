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
from ai_gateway.schemas.openai_embeddings import CreateEmbeddingsRequest, CreateEmbeddingsResponse
from ai_gateway.schemas.openai_models import ListResponse, Model

# Module-level provider instances for dependency injection
_default_custom_provider: CustomProcessingProvider | None = None
_default_cerebras_provider: CerebrasProvider | None = None
_default_ollama_provider: OllamaProvider | None = None


def get_custom_provider() -> CustomProcessingProvider:
    """Factory dependency for CustomProcessingProvider."""
    global _default_custom_provider
    if _default_custom_provider is None:
        _default_custom_provider = CustomProcessingProvider()
    return _default_custom_provider


def get_cerebras_provider() -> CerebrasProvider:
    """Factory dependency for CerebrasProvider."""
    global _default_cerebras_provider
    if _default_cerebras_provider is None:
        _default_cerebras_provider = CerebrasProvider()
    return _default_cerebras_provider


def get_ollama_provider() -> OllamaProvider:
    """Factory dependency for OllamaProvider."""
    global _default_ollama_provider
    if _default_ollama_provider is None:
        _default_ollama_provider = OllamaProvider()
    return _default_ollama_provider


# Module-level dependency instances
_custom_provider_dep = Depends(get_custom_provider)
_cerebras_provider_dep = Depends(get_cerebras_provider)
_ollama_provider_dep = Depends(get_ollama_provider)


health_router = APIRouter()
v1_router = APIRouter(prefix=V1_BASE)
cerebras_router = APIRouter(prefix=CEREBRAS_BASE)
ollama_router = APIRouter(prefix=OLLAMA_BASE)


@health_router.get(HEALTHZ)
async def healthz() -> dict[str, str | int]:
    """Readiness/health endpoint. No auth required.

    Returns minimal status and, if available, version/build metadata.
    """
    payload: dict[str, str | int] = {"status": "ok"}
    # Best-effort: include version/build if the package exposes them.
    import ai_gateway

    version = getattr(ai_gateway, "__version__", None)
    build = getattr(ai_gateway, "__build__", None)

    if version is not None:
        payload["version"] = str(version)
    if build is not None:
        # build could be a short git sha or build number
        payload["build"] = str(build)
    return payload


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
    req: ChatCompletionRequest,
    token: str = Depends(auth_bearer),
    provider: CustomProcessingProvider = _custom_provider_dep,
) -> ChatCompletionResponse:
    # Use the CustomProcessingProvider to generate a response
    return await provider.chat_completions(req)


@v1_router.get("/models")
async def list_models_v1(
    token: str = Depends(auth_bearer),
    provider: CustomProcessingProvider = _custom_provider_dep,
) -> ListResponse[Model]:
    return await provider.list_models()


@v1_router.post("/embeddings")
async def create_embeddings_v1(
    req: CreateEmbeddingsRequest,
    token: str = Depends(auth_bearer),
    provider: CustomProcessingProvider = _custom_provider_dep,
) -> CreateEmbeddingsResponse:
    return await provider.create_embeddings(req)


@cerebras_router.post("/chat/completions")
async def chat_completions_cerebras(
    req: ChatCompletionRequest,
    token: str = Depends(auth_bearer),
    provider: CerebrasProvider = _cerebras_provider_dep,
) -> ChatCompletionResponse:
    try:
        return await provider.chat_completions(req)
    except ProviderError as exc:
        # Re-raise to be handled by global exception handlers as 502 with standardized payload
        raise exc


@cerebras_router.get("/models")
async def list_models_cerebras(
    token: str = Depends(auth_bearer),
    provider: CerebrasProvider = _cerebras_provider_dep,
) -> ListResponse[Model]:
    try:
        return await provider.list_models()
    except ProviderError as exc:
        raise exc


@cerebras_router.post("/embeddings")
async def create_embeddings_cerebras(
    req: CreateEmbeddingsRequest,
    token: str = Depends(auth_bearer),
    provider: CerebrasProvider = _cerebras_provider_dep,
) -> CreateEmbeddingsResponse:
    try:
        return await provider.create_embeddings(req)
    except ProviderError as exc:
        raise exc


@ollama_router.post("/chat/completions")
async def chat_completions_ollama(
    req: ChatCompletionRequest,
    token: str = Depends(auth_bearer),
    provider: OllamaProvider = _ollama_provider_dep,
) -> ChatCompletionResponse:
    try:
        return await provider.chat_completions(req)
    except ProviderError as exc:
        # Re-raise to be handled by global exception handlers as 502 with standardized payload
        raise exc


@ollama_router.get("/models")
async def list_models_ollama(
    token: str = Depends(auth_bearer),
    provider: OllamaProvider = _ollama_provider_dep,
) -> ListResponse[Model]:
    try:
        return await provider.list_models()
    except ProviderError as exc:
        raise exc


@ollama_router.post("/embeddings")
async def create_embeddings_ollama(
    req: CreateEmbeddingsRequest,
    token: str = Depends(auth_bearer),
    provider: OllamaProvider = _ollama_provider_dep,
) -> CreateEmbeddingsResponse:
    try:
        return await provider.create_embeddings(req)
    except ProviderError as exc:
        raise exc
