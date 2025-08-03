# Streaming Compatibility Plan — OpenAI Parity and Ollama Integration

Date: 2025-08-03

Objective
Achieve OpenAI-compatible streaming for Chat Completions across our providers starting with Ollama, resolve the “502 Streaming is not supported in v1.0” error, and verify request ID propagation and parameter naming alignment with OpenAI Python SDK v1.x.

---

## 1) Findings and Root Cause Analysis

1.1 Error observed
- 502 Streaming is not supported in v1.0
- Request ID: mdvsue72-00c3b984 (example presented by user)
- Current code explicitly rejects streaming:
  - OllamaProvider.chat_completions:
    - If req.stream is True → raise ProviderError("Streaming is not supported in v1.0")
  - OllamaClient.chat(enforced non-stream):
    - Raises httpx.RequestError if stream True; body always sets stream=False.
- Root cause: We intentionally disabled streaming for v1.0. The AI agent expects stream=true (OpenAI-compatible), but the stack rejects it. Therefore a 5xx is returned via ProviderError mapping.

1.2 Request ID propagation
- Middleware: CorrelationIdMiddleware sets both "X-Request-ID" and "x-request-id" on responses, accepts either header on input, and stores request ID in a contextvar.
- Error handlers: _json_response injects both headers onto error responses if available.
- Clients retrieving request_id:
  - OpenAI SDK surfaces response._request_id sourced from "x-request-id" response header (not request body).
- “request_id parameter” reference:
  - OpenAI does NOT use a request_id field in the JSON body for chat completions; it’s an HTTP header in responses. Some SDKs allow passing extra headers. There is no standard JSON parameter named "request_id" in Chat Completions requests.
- Conclusion: Parameter naming is correct on our side; ensure:
  - Response headers always include x-request-id (already done).
  - Outbound provider calls forward X-Request-ID (OllamaClient headers do this best-effort).
  - Logs should include request_id from contextvar (already supported by logging middleware and setup).

1.3 OpenAI streaming expectations (SDK v1.x)
- ChatCompletions supports streaming via SSE/event-stream (text-delta chunks or structured events).
- Python SDK usage:
  - client.chat.completions.create(..., stream=True) → requires event/streaming response.
  - SDK also supports `.with_streaming_response` context manager for raw streaming (headers accessible).
- We currently:
  - Lack a streaming endpoint/route.
  - Return non-streaming JSON only.
  - Reject stream flag.

1.4 Ollama streaming expectations
- Ollama chat supports streaming via:
  - POST /api/chat with "stream": true yields incremental chunks of JSON lines or SSE depending on server/version. Latest recommends SSE-like progress but historically JSONL.
- For maximum compatibility:
  - We need server-side streaming mode that:
    - Maps OpenAI Chat Completions request to Ollama chat stream.
    - Adapts Ollama chunk format to OpenAI chat.completion.chunk events (or a close equivalent).
    - Sets Content-Type: text/event-stream; transfer-encoding: chunked; flush events as they arrive.
  - If strict chunk schema parity is not feasible, aim for minimal compatible shape commonly parsed by SDKs (id, object="chat.completion.chunk", choices with delta, finish_reason, and accumulated usage when done).

---

## 2) Requirements for OpenAI-Compatible Streaming

2.1 API semantics
- Endpoint: POST /<namespace>/v1/chat/completions with stream=true.
- Response: stream of events (“chunks”) until final message with finish_reason, followed by usage (optional) in a terminal event or as part of final payload.
- Headers:
  - Include x-request-id on the streaming response (and canonical X-Request-ID).
  - Keep connection open; send heartbeats/comments if needed to prevent proxy timeouts.
- Error handling:
  - If upstream fails mid-stream, send an error event and close.
  - Normalize network errors to a terminal error response if possible.

2.2 Event model (minimal viable)
- Use OpenAI-like chunk objects:
  - {"id": "...", "object": "chat.completion.chunk", "created": epoch, "model": "...", "choices": [{"index": 0, "delta": {"content": "..."}, "finish_reason": None}]}
- On completion:
  - Final chunk has finish_reason = "stop" (or mapped reason) and no delta content.
  - Optionally emit a usage event or provide usage in a final non-chunk envelope; SDKs typically compute usage after end.

---

## 3) Technical Plan

3.1 Routing and FastAPI streaming support
- Add streaming-aware route handlers for:
  - /v1/chat/completions, /ollama/v1/chat/completions, /cerebras/v1/chat/completions
- For requests with stream=true:
  - Return a StreamingResponse or EventSourceResponse (SSE) with an async generator that yields encoded chunks.

3.2 Provider abstraction
- Update providers/base.py:
  - Extend ChatProvider to include an async stream_chat_completions(self, req: ChatCompletionRequest) -> AsyncIterator[dict[str, Any]] interface (or a richer typed chunk model).
  - Keep existing chat_completions for non-streaming.
- OllamaProvider:
  - Implement stream_chat_completions that:
    - Calls OllamaClient.chat(..., stream=True)
    - Iterates over upstream chunks and maps them to OpenAI-like chunk dicts.
    - Handles end-of-stream markers and converts finish_reason.
- CerebrasProvider:
  - Mark as not implemented initially (return 501/Not Implemented) or reuse non-streaming path and ignore stream flag. Document limitation.

3.3 Client wrapper
- OllamaClient:
  - Add chat_stream(...) method that:
    - POSTs to /api/chat with "stream": true
    - Consumes an async byte iterator or SSE via httpx (requires using client.stream method).
    - Parses chunked JSON (Ollama formats) incrementally and yields normalized dicts upstream → provider handles mapping.
  - Ensure headers include X-Request-ID.

3.4 Mapping logic
- From Ollama chunk format to OpenAI chunk:
  - When chunk includes message content delta: produce choices[0].delta.content = text.
  - When chunk indicates completion: produce final chunk with finish_reason mapped via existing _map_finish_reason helper (or a local equivalent).
  - Maintain consistent id across chunks (e.g., chatcmpl-<uuid>).
  - created = first-chunk timestamp (or now).
  - model = req.model.
- Usage: optional; if Ollama provides eval/prompt counts at the end, emit a final non-chunk usage event if needed (some SDKs don’t require it in streaming).

3.5 Middleware and headers
- Ensure StreamingResponse sets headers:
  - X-Request-ID and x-request-id on initial response.
  - Proper Cache-Control: no-cache, Connection: keep-alive, Transfer-Encoding: chunked (implicit).
- Confirm correlation middleware applies to streaming path as well.

3.6 Fallback behavior
- If an agent sets stream=true but provider streaming is unavailable:
  - For now, return 501 Not Implemented with error payload including type and message:
    - {"error":{"type":"not_implemented","message":"Streaming not yet supported for this provider"}}
  - Alternatively, fall back to non-streaming and return a single non-stream response (less expected by clients). Prefer explicit 501.

---

## 4) Parameter Names and Headers Verification (OpenAI SDK v1.x)

4.1 Stream parameter
- Correct param: "stream": true (boolean) in the request body for Chat Completions.
- Our schemas accept "stream" and "stream_options" already. Good.

4.2 Request ID parameter
- OpenAI does not define a JSON body field named "request_id" for Chat Completions. Request IDs are conveyed in HTTP response headers (x-request-id).
- Our stack:
  - Adds "X-Request-ID" and "x-request-id" on every response.
  - Best-effort forwards "X-Request-ID" to upstream provider (OllamaClient headers).
- Action: No change to JSON parameter names; ensure headers present on streaming responses.

4.3 Other parameters
- Keep permissive extras on requests (extra="ignore") to accept evolving SDK fields like response_format, tools, etc.

---

## 5) Step-by-Step Implementation Plan

Phase S1 — Plumbing and Interfaces
1) Update ai_gateway/providers/base.py:
   - Add stream_chat_completions(...) async generator signature to ChatProvider.
2) Update routes:
   - In src/ai_gateway/api/routes.py (namespaced routes):
     - Detect req.stream is True.
     - Dispatch to provider.stream_chat_completions if implemented, otherwise:
       - Return 501 with standardized error payload.

Phase S2 — Ollama streaming implementation
1) ai_gateway/providers/ollama_client.py:
   - Add async def chat_stream(..., stream=True) -> AsyncIterator[dict[str, Any]]:
     - Use httpx.AsyncClient.stream("POST", "/api/chat", json=..., headers=...) to read lines/chunks.
     - Parse per-chunk JSON; yield dicts to provider.
2) ai_gateway/providers/ollama.py:
   - Implement stream_chat_completions that:
     - Creates an id and created timestamp once.
     - Iterates upstream chunks and maps them to OpenAI chunk dicts:
       - object: "chat.completion.chunk"
       - choices: [{"index":0, "delta":{"content": piece}, "finish_reason": None}]
     - Emit final chunk with finish_reason.
   - Error handling: wrap upstream exceptions → ProviderError (502); terminate stream.

Phase S3 — Headers and SSE polish
1) Use StreamingResponse (or sse-starlette EventSourceResponse if available) with:
   - media_type="text/event-stream"
   - Proper headers (including X-Request-ID/x-request-id)
2) Ensure correlation middleware remains effective: Contextvar is set before building StreamingResponse.

Phase S4 — Tests and Docs
1) Add unit tests for:
   - routes returning StreamingResponse when stream=True
   - ollama_client.chat_stream parsing: simulated httpx stream yielding JSON lines; generator yields dicts.
   - provider mapping to OpenAI chunk format.
   - Error: provider raises → 502 end-of-stream behavior.
2) Update docs:
   - docs/OAI-Standards/OAI-CHANGE-LOG.md → Phase “Streaming” section and status.
   - README.md → streaming support notes and example curl using --no-buffer and Accept: text/event-stream.

---

## 6) Risk, Limitations, and Mitigations

- SSE vs JSONL: Ollama variants may differ; we will parse JSON lines from httpx response content. If SSE needed, consider sse-starlette.
- Proxy buffering: Add headers to discourage buffering (Cache-Control: no-cache). Recommend clients use proper streaming handling.
- Provider differences: Cerebras streaming may be deferred; return 501 there initially.
- Compatibility: SDK expects OpenAI chunk schema; our mapping aims to be minimal but acceptable (delta.content chunks and final finish_reason). Future refinement can add tool_calls/logprobs in streaming if available.

---

## 7) Acceptance Criteria

- When stream=true:
  - Endpoint returns 200 with Content-Type: text/event-stream and incremental chunks.
  - Headers include both X-Request-ID and x-request-id.
  - Ollama-backed namespaces (/ollama/v1/chat/completions) stream content deltas until completion.
- When stream=true on unsupported provider:
  - Return 501 with standardized JSON error.
- Non-stream requests continue to work unchanged.

---

## 8) Work Estimate

- S1 (interfaces/routing): 2–3 hrs
- S2 (Ollama streaming): 4–6 hrs (including chunk mapping)
- S3 (headers/SSE polish): 1–2 hrs
- S4 (tests/docs): 3–5 hrs

Total: ~10–16 hrs

---

## 9) Next Steps

Decision captured:
- Transport: Server-Sent Events (SSE, text/event-stream).
- Non-Ollama providers behavior when stream=true: return 501 Not Implemented.

Implementation will proceed with S1–S4 iteratively:
- Start with base interface and routing guard (S1).
- Implement Ollama client streaming and provider adapter (S2).
- Add SSE headers and polish (S3).
- Add tests and documentation updates (S4).

Progress log:
- [x] S1 — Provider interface + routing: COMPLETE
  - Routers updated to feature-detect stream=true; return 501 JSON for non-streaming providers.
  - Endpoints now set response_model=None for StreamingResponse/JSONResponse unions to avoid FastAPI modeling errors.
- [x] S2 — Ollama streaming client + provider mapping: COMPLETE
  - httpx.AsyncClient.stream used to POST /api/chat with "stream": true.
  - Robust parsing for both JSONL and SSE-framed "data:" lines; ignores [DONE] sentinels from upstream.
  - Coerces list-based message content to string for Ollama v0.10.1 to prevent 400 Bad Request.
  - Provider maps upstream chunks to OpenAI-compatible chunk events and emits final chunk with finish_reason.
- [x] S3 — SSE headers/polish: COMPLETE
  - StreamingResponse with media_type="text/event-stream".
  - Emits events as "data: {json}\n\n" and terminates with "data: [DONE]\n\n".
  - Correlation headers included: "X-Request-ID" and "x-request-id". Cache-Control: no-cache ensured.
- [?] S4 — Tests/docs updates: NEXT
  - Add tests for streaming routes (Ollama happy path, 501 for unsupported providers).
  - Add Ollama client parsing tests (JSONL/SSE/[DONE], content coercion).
  - Add provider mapping tests (delta chunks and finalization).
  - Update README with curl -N streaming example and header notes.
