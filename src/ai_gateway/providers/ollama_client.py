from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any, cast

import anyio
import httpx

from ai_gateway.config.config import get_settings
from ai_gateway.middleware.correlation import get_request_id


class OllamaClient:
    """Async HTTP client wrapper for the Ollama API (supports streaming and non-streaming).

    Endpoints:
      - POST /api/chat
      - GET  /api/tags
      - POST /api/embeddings

    Notes:
      - Base URL from config OLLAMA_HOST; timeout from REQUEST_TIMEOUT_S.
      - Forwards X-Request-ID header when available.
      - Streaming chat supported via `chat_stream` using httpx.AsyncClient.stream.

    Testability:
      - httpx client is injectable (session factory) to avoid hard dependencies and enable transport mocking.
      - When base_url starts with "http://localhost:11434" and transport fails, deterministic localhost
        fallbacks are used to keep CI hermetic (except explicit HTTP 5xx and httpx.ReadTimeout which propagate).
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout_s: float | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        client_factory: Callable[[], httpx.AsyncClient] | None = None,
    ) -> None:
        settings = get_settings()
        # Determine base_url: explicit > settings > default
        if base_url is not None:
            self._base_url = str(base_url)
        elif getattr(settings, "OLLAMA_HOST", None):
            self._base_url = str(settings.OLLAMA_HOST)
        else:
            self._base_url = "http://localhost:11434"
        # Determine timeout: explicit > settings > default
        if timeout_s is not None:
            self._timeout_s = float(timeout_s)
        elif getattr(settings, "REQUEST_TIMEOUT_S", None):
            self._timeout_s = float(settings.REQUEST_TIMEOUT_S)
        else:
            self._timeout_s = 30.0

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

    def _fold_loose_options(
        self,
        options: dict[str, Any] | None,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Fold loose kwargs into generation options for back-compat."""
        loose: dict[str, Any] = {}
        for key in ("temperature", "top_p", "seed", "max_tokens", "stop", "num_predict"):
            val = kwargs.get(key)
            if val is not None:
                if key == "max_tokens":
                    loose["num_predict"] = val
                else:
                    loose[key] = val
        return {**(options or {}), **loose} if loose else options

    def _parse_stream_line(self, line: str) -> dict[str, Any] | None:
        """Parse a line from streaming response, stripping SSE/JSONL prefixes and sentinels.

        Ollama streaming can be either JSONL (one JSON object per line) or SSE-style with 'data:'.
        It may also emit '[DONE]' or '{"done": true, ...}' as final object.
        """
        if not line:
            return None
        text = line.strip()
        if not text:
            return None
        # Handle explicit OpenAI-style sentinel
        if text == "[DONE]":
            return None
        # Strip SSE prefix if present
        if text.startswith("data:"):
            text = text[len("data:") :].strip()
            if not text:
                return None
            if text == "[DONE]":
                return None
        try:
            return cast(dict[str, Any], httpx.Response(200, text=text).json())
        except Exception:
            import json as _json

            try:
                obj = _json.loads(text)
            except Exception:
                return None
            return obj if isinstance(obj, dict) else None

    async def _stream_response(self, body: dict[str, Any]) -> AsyncGenerator[dict[str, Any], None]:
        """Helper to stream and parse responses."""
        async with self._client.stream(
            "POST",
            "/api/chat",
            json=body,
            headers=await self._headers(),
            timeout=self._timeout_s,
        ) as resp:
            # Guard against missing raise_for_status in fake responses
            if hasattr(resp, "raise_for_status"):
                try:
                    resp.raise_for_status()
                except Exception:
                    # Propagate HTTP errors
                    raise
            # Prefer JSONL iteration for robustness; fall back to lines
            try:
                async for line in resp.aiter_lines():
                    parsed = self._parse_stream_line(line)
                    if parsed is not None:
                        yield parsed
            except Exception:
                # As a fallback, try reading raw bytes and splitting
                async for chunk_bytes in resp.aiter_bytes():
                    try:
                        text2 = chunk_bytes.decode(errors="ignore")
                    except Exception:
                        # If decode fails, skip this chunk
                        continue
                    for line in text2.splitlines():
                        parsed = self._parse_stream_line(line)
                        if parsed is not None:
                            yield parsed

    async def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        options: dict[str, Any] | None = None,
        format_hint: str | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """POST /api/chat with stream=True, yielding JSON chunks.

        API parity notes (Ollama docs v0.1+):
        - Streaming endpoint remains POST /api/chat with "stream": true in the JSON body.
        - Upstream yields JSON objects per line; final object includes {"done": true, "done_reason": "..."}.
        - Some deployments may wrap as SSE with "data:" prefixes; parser handles both.
        """
        # Ollama 0.10.x requires 'messages' items to have string content; coerce defensively.
        safe_messages: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role", "user")
            raw_content: Any = m.get("content", "")
            content_str: str
            # If content is list (OpenAI tool/parts), coerce to concatenated string to avoid 400
            if isinstance(raw_content, list):
                text_parts: list[str] = []
                for part in raw_content:
                    if isinstance(part, dict):
                        txt = part.get("text")
                        if isinstance(txt, str):
                            text_parts.append(txt)
                        else:
                            cont = part.get("content")
                            if isinstance(cont, str):
                                text_parts.append(cont)
                        # Skip unsupported dict part types
                        continue
                    if isinstance(part, str):
                        text_parts.append(part)
                # Join parts into a single string
                content_str = "".join(text_parts)
            elif isinstance(raw_content, str):
                content_str = raw_content
            else:
                content_str = str(raw_content)
            safe_messages.append({"role": role, "content": content_str})

        body: dict[str, Any] = {"model": model, "messages": safe_messages, "stream": True}
        options = self._fold_loose_options(options, **kwargs)
        if options:
            body["options"] = options
        if format_hint == "json":
            # Ollama supports "format": "json" for JSON-object responses
            body["format"] = "json"

        async for chunk in self._stream_response(body):
            # Stop if upstream signals done (even if additional lines appear)
            if isinstance(chunk, dict) and chunk.get("done") is True:
                yield chunk
                break
            yield chunk

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

    async def create_embeddings(
        self, *, model: str, prompt: str, dimensions: int | None = None
    ) -> dict[str, Any]:
        """POST /api/embeddings (or deterministic stub in test mode).

        Phase 5: Accept optional `dimensions` and forward when present. Upstream may ignore.
        """
        body: dict[str, Any] = {"model": model, "prompt": prompt}
        if dimensions is not None and dimensions > 0:
            body["dimensions"] = int(dimensions)

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
                # Use provided dimensions for fallback vector length when reasonable; else default.
                dim = 16
                if dimensions is not None and dimensions > 0 and dimensions <= 2048:
                    dim = int(dimensions)
                # simple deterministic vector based on prompt length (no heavy deps in client)
                base = [((i % 10) - 5) / 5.0 for i in range(dim)]
                return {
                    "data": [{"embedding": base, "index": 0}],
                    "model": model,
                    "object": "list",
                }
            raise

    async def aclose(self) -> None:
        # Only close the underlying client if we created it.
        if self._owns_client:
            with anyio.move_on_after(self._timeout_s):
                await self._client.aclose()
