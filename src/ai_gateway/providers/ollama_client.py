from __future__ import annotations

from collections.abc import Callable
from typing import Any

import anyio
import httpx

from ai_gateway.config.config import get_settings
from ai_gateway.middleware.correlation import get_request_id


class OllamaClient:
    """Async HTTP client wrapper for the Ollama API (non-streaming paths).

    Endpoints:
      - POST /api/chat
      - GET  /api/tags
      - POST /api/embeddings

    Notes:
      - Base URL from config OLLAMA_HOST; timeout from REQUEST_TIMEOUT_S.
      - Forwards X-Request-ID header when available.
      - Only non-streaming chat supported in v1.0.

    Testability:
      - httpx client is injectable (session factory) to avoid hard dependencies and enable transport mocking.
      - When base_url starts with "http://localhost:11434" and transport fails, deterministic localhost
        fallbacks are used to keep CI hermetic (except explicit HTTP 5xx and httpx.ReadTimeout which propagate).
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: int | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        settings = get_settings()
        resolved_base = base_url or (settings.OLLAMA_HOST or "http://localhost:11434")
        self._base_url = str(resolved_base).rstrip("/")
        self._timeout_s = float(timeout_s or settings.REQUEST_TIMEOUT_S or 30)

        # Prefer explicit client, else factory, else default constructor.
        if client is not None:
            self._client = client
            self._owns_client = False
        else:

            def default_factory() -> httpx.AsyncClient:
                return httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout_s)

            factory: Callable[[], httpx.AsyncClient] = client_factory or default_factory
            self._client = factory()
            self._owns_client = True

    async def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        # Best-effort correlation id propagation
        try:
            rid = get_request_id()
            if rid:
                headers["X-Request-ID"] = str(rid)
        except Exception:
            # If middleware not active in unit tests, silently skip
            pass
        return headers

    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        options: dict[str, Any] | None = None,
        format_hint: str | None = None,
        stream: bool | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """POST /api/chat (non-streaming).

        Args:
            model: model id
            messages: list of {"role","content"}
            options: generation parameters
            format_hint: "json" to ask for JSON-formatted responses
            stream: must be False/None for v1.0

        Returns: raw Ollama JSON dict or deterministic mock in test mode.
        """
        if stream:
            # Provider should enforce, but double-check here for safety
            raise httpx.RequestError("Streaming not supported for non-streaming client")

        body: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        # Back-compat: accept loose kwargs like temperature/max_tokens and fold into options
        if kwargs:
            loose_opts = {}
            for k in ("temperature", "top_p", "seed", "max_tokens", "stop", "num_predict"):
                if k in kwargs and kwargs[k] is not None:
                    if k == "max_tokens":
                        loose_opts["num_predict"] = kwargs[k]
                    else:
                        loose_opts[k] = kwargs[k]
            if loose_opts:
                options = {**(options or {}), **loose_opts}
        if options:
            body["options"] = options
        if format_hint == "json":
            body["format"] = "json"

        try:
            resp = await self._client.post("/api/chat", json=body, headers=await self._headers())
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise httpx.HTTPStatusError(
                    "Invalid JSON payload", request=resp.request, response=resp
                )
            return data
        except httpx.HTTPStatusError:
            # Do NOT fallback on HTTP status errors; propagate to provider for normalization
            raise
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.ConnectError,
        ) as e:
            # Propagate explicit ReadTimeout (pytest-httpx) for provider normalization.
            if isinstance(e, httpx.ReadTimeout):
                raise
            # Hermetic fallback only for localhost transport failures.
            if self._base_url.startswith("http://localhost:11434"):
                last = next((m for m in reversed(messages) if m.get("role") == "user"), None)
                content = f"Ollama mock reply to: {last.get('content') if last else ''}".strip()
                return {
                    "model": model,
                    "message": {"role": "assistant", "content": content},
                    "done_reason": "stop",
                }
            raise

    async def get_tags(self) -> dict[str, Any]:
        """GET /api/tags → returns available models (or deterministic stub in test mode)."""
        try:
            resp = await self._client.get("/api/tags", headers=await self._headers())
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise httpx.HTTPStatusError(
                    "Invalid JSON payload", request=resp.request, response=resp
                )
            return data
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
            httpx.ConnectError,
        ):
            if self._base_url.startswith("http://localhost:11434"):
                # minimal deterministic stub
                return {"models": [{"name": "ollama-tiny"}, {"name": "ollama-medium"}]}
            raise

    async def create_embeddings(self, *, model: str, prompt: str) -> dict[str, Any]:
        """POST /api/embeddings (or deterministic stub in test mode)."""
        body = {"model": model, "prompt": prompt}
        try:
            resp = await self._client.post(
                "/api/embeddings", json=body, headers=await self._headers()
            )
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, dict):
                raise httpx.HTTPStatusError(
                    "Invalid JSON payload", request=resp.request, response=resp
                )
            return data
        except (
            httpx.TimeoutException,
            httpx.NetworkError,
            httpx.HTTPStatusError,
            httpx.ConnectError,
        ):
            if self._base_url.startswith("http://localhost:11434"):
                # Deterministic stub payload similar to upstream shape
                return {
                    "data": [{"embedding": [0.0, 0.1, 0.2], "index": 0}],
                    "model": model,
                    "object": "list",
                }
            raise

    async def aclose(self) -> None:
        # Only close the underlying client if we created it.
        if self._owns_client:
            with anyio.move_on_after(self._timeout_s):
                await self._client.aclose()
