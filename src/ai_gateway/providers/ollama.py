from __future__ import annotations

import time
import uuid
from typing import Any

from ai_gateway.config.config import get_settings
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
        # Defer settings resolution to the injected or constructed client.
        # In tests, pass a preconstructed OllamaClient that already sees patched settings.
        self._client = client or OllamaClient()

    # ---- Internal helpers to keep complexity low ----

    @staticmethod
    def _messages_to_dicts(messages: list[ChatMessage]) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    @staticmethod
    def _format_hint(req: ChatCompletionRequest) -> str | None:
        try:
            rf = getattr(req, "response_format", None)
            if isinstance(rf, dict) and rf.get("type") == "json_object":
                return "json"
        except Exception:
            return None
        return None

    @staticmethod
    def _build_options(req: ChatCompletionRequest, format_hint: str | None) -> dict[str, Any]:
        options: dict[str, Any] = {}
        field_map: dict[str, str] = {
            "max_tokens": "num_predict",
            "stop": "stop",
            "temperature": "temperature",
            "top_p": "top_p",
            "seed": "seed",
            "top_k": "top_k",
            "presence_penalty": "presence_penalty",
            "frequency_penalty": "frequency_penalty",
            "logprobs": "logprobs",
            "logit_bias": "logit_bias",
            "n": "n",
            "user": "user",
        }
        for src, dst in field_map.items():
            val = getattr(req, src, None)
            if val is not None:
                if src == "stop" and isinstance(val, str):
                    options[dst] = [val]
                else:
                    options[dst] = val

        # Tools/function capture for future orchestration
        for k in ("tools", "tool_choice", "function_call"):
            v = getattr(req, k, None)
            if v is not None:
                options[k] = v

        # Optional enrichment toggle (single flag)
        enable_enrichment = False
        try:
            settings = get_settings()
            enable_enrichment = bool(getattr(settings, "ENABLE_ENRICHMENT", False))
        except Exception:
            enable_enrichment = False

        if format_hint == "json":
            options.setdefault("structured", True)
            if enable_enrichment:
                options.setdefault("enforce_structured", True)
        if enable_enrichment:
            options.setdefault("enrichment", {"enabled": True})

        return options

    @staticmethod
    def _map_response_to_openai(raw: dict[str, Any], req_model: str) -> ChatCompletionResponse:
        created_at = (raw.get("created_at") or "").strip()
        created = _now_epoch()
        if created_at:
            try:
                ts = created_at.replace("Z", "+00:00")
                created = int(int(__import__("datetime").datetime.fromisoformat(ts).timestamp()))
            except Exception:
                created = _now_epoch()

        completion_id = _gen_id()
        assistant_msg = ChatMessage(
            role="assistant", content=(raw.get("message") or {}).get("content", "")
        )
        choice = Choice(index=0, message=assistant_msg, finish_reason="stop")

        prompt_tokens = int(raw.get("prompt_eval_count", 0) or 0)
        completion_tokens = int(raw.get("eval_count", 0) or 0)
        total_tokens = prompt_tokens + completion_tokens
        usage = Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        return ChatCompletionResponse(
            id=completion_id,
            object="chat.completion",
            created=created,
            model=req_model,
            choices=[choice],
            usage=usage,
        )

    async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse:
        # Enforce non-streaming in v1.0
        if getattr(req, "stream", False):
            raise ProviderError("Streaming is not supported in v1.0")

        in_messages = self._messages_to_dicts(req.messages)
        format_hint = self._format_hint(req)
        options = self._build_options(req, format_hint)

        try:
            raw: dict[str, Any] = await self._client.chat(
                model=req.model,
                messages=in_messages,
                options=options or None,
                format_hint=format_hint,
                stream=False,
            )
            # Defensive: http client may bubble httpx.HTTPStatusError or return non-dict JSON.
            if not isinstance(raw, dict):
                raise ProviderError("Upstream provider error")
        except Exception as exc:
            # Normalize any client/upstream failure into ProviderError (handled as 502)
            raise ProviderError("Upstream provider error") from exc

        return self._map_response_to_openai(raw, req.model)

    async def list_models(self) -> ListResponse[Model]:
        """Map GET /api/tags from Ollama to OpenAI ListResponse[Model]."""
        try:
            raw = await self._client.get_tags()
        except Exception as exc:
            raise ProviderError("Upstream provider error") from exc

        # Expected shape (fallback stub): {"models": [{"name": "llama3"}, ...]}.
        items = raw.get("models") if isinstance(raw, dict) else None
        if not isinstance(items, list):
            items = []

        now = _now_epoch()
        out: list[Model] = []
        for it in items:
            name = (it or {}).get("name")
            created_at = (it or {}).get("modified_at") or (it or {}).get("created_at")
            created = now
            if isinstance(created_at, str) and created_at:
                try:
                    ts = created_at.replace("Z", "+00:00")
                    created = int(__import__("datetime").datetime.fromisoformat(ts).timestamp())
                except Exception:
                    created = now
            perm = ModelPermission(
                id=f"perm-{uuid.uuid4().hex}",
                created=created,
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
            if isinstance(name, str) and name:
                out.append(
                    Model(
                        id=name,
                        created=created,
                        owned_by="ollama",
                        permission=[perm],
                        root=None,
                        parent=None,
                    )
                )
        return ListResponse[Model](data=out)

    async def create_embeddings(self, req: CreateEmbeddingsRequest) -> CreateEmbeddingsResponse:
        """Create embeddings via Ollama /api/embeddings with router-first normalization."""
        items = normalize_input_to_strings(req.input)

        data: list[EmbeddingItem] = []
        # v1.0 simplicity: sequential calls for each input to keep behavior predictable
        for idx, text in enumerate(items):
            try:
                raw = await self._client.create_embeddings(model=req.model, prompt=text)
            except Exception as exc:
                raise ProviderError("Upstream provider error") from exc
            # Expected shape from client/fallback: {"data": [{"embedding": [...], "index": 0}], "model": "..."}
            vec = None
            if isinstance(raw, dict):
                arr = raw.get("data")
                if isinstance(arr, list) and arr:
                    first = arr[0]
                    if isinstance(first, dict):
                        vec = first.get("embedding")
            if not isinstance(vec, list):
                # Fallback to deterministic vector to avoid failures in dev if upstream changes
                vec = deterministic_vector(text, dim=16)
            data.append(EmbeddingItem(embedding=vec, index=idx))

        # Usage accounting: conservative zeros (upstream does not provide usage)
        usage = EmbeddingUsage(prompt_tokens=0, total_tokens=0)
        return CreateEmbeddingsResponse(object="list", data=data, model=req.model, usage=usage)
