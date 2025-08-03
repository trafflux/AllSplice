# OLLAMA — TODO (v1.0 scope aligned with Core OSI)

Status Date: 2025-08-03

Scope reminder (v1.0):
- In-scope: GET /<namespace>/models, POST /<namespace>/embeddings, POST /<namespace>/chat/completions
- Out-of-scope: Legacy Completions endpoint, Streaming

This TODO tracks remaining tasks to complete the Ollama Provider PRD within v1.0 scope.

## 1) Provider Implementation Gaps

1.1 Chat Completions mapping — options and format
- Add options mapping in provider to pass generation params to the client (future httpx impl):
  - num_predict <- max_tokens
  - stop <- stop
  - temperature <- temperature
  - top_p <- top_p
  - seed <- seed
- Translate response_format {"type":"json_object"} to format="json".
- Enforce non-streaming: if req.stream is True, raise ProviderError with standard message.
- Status: ✅ (Provider layer implemented in src/ai_gateway/providers/ollama.py; mock client ignores options/format for now. No behavior change to responses.)

1.2 Usage fields for Chat Completions
- If upstream provides prompt_eval_count / eval_count, map to usage; else default to zeros.
- Add fallback: created from upstream created_at to epoch (fallback to now on parse error).
- Status: ✅ (implemented: usage mapping + created_at→epoch fallback)

1.3 List Models mapping (real client)
- Replace deterministic stub in provider with mapping from GET /api/tags via client.
- Convert modified_at (ISO8601) to epoch seconds with robust parsing.
- Status: ✅ (implemented in provider using client.get_tags with timestamp parsing)

1.5 OpenAI pass-through router parity (foundational)
- Ensure provider layer can intercept and pass-through every OpenAI Chat Completions option/field to Ollama equivalents (or include in options) to achieve “router-first” parity:
  - temperature, top_p, top_k (map to options.top_k), presence_penalty/frequency_penalty (no direct Ollama support → include in options for future server-side use), stop (list), seed, max_tokens→num_predict, logprobs/logit_bias (capture under options for future), user, response_format (json_object→format=json; text otherwise), tools/tool_choice (capture under options.tools for future orchestration), n (best_of proxy), function_call/tool_calls (for future).
- Structured responses emphasis: wire response_format hints as early as possible; add placeholder ‘structured’ key in options for future strict schema validation on server side (no-op for now).
- Status: ✅ (implemented in provider.chat_completions; options built via single mapping function)

1.4 Embeddings (real client) and batching
- Replace deterministic embeddings with POST /api/embeddings via client.
- Support input: str | list[str]; Strategy B (aggregate multiple items) preferred.
- usage: prompt_tokens and total_tokens set to 0 (upstream doesn’t provide usage).
- Status: ✅ (implemented sequential per-item calls with normalization and deterministic fallback)

## 2) Client (OllamaClient) — Real HTTP I/O

2.1 httpx.AsyncClient integration
- Base URL: OLLAMA_HOST (config), Timeout: REQUEST_TIMEOUT_S.
- Headers: Content-Type: application/json; include X-Request-ID if available.
- Methods:
  - get_tags() → GET /api/tags
  - create_embeddings(model, prompt) → POST /api/embeddings
  - chat(model, messages, options, stream=false, format?) → POST /api/chat
- Router-first fallback:
  - When OLLAMA_HOST points to localhost and unreachable, fall back to deterministic stubs (chat/tags/embeddings) to keep CI and agent development hermetic.
- Status: ✅ (real HTTP implemented; localhost hermetic fallbacks preserved; options/format mapping handled at provider; header propagation verified in tests)

2.2 Error normalization and timeouts
- Convert httpx errors, timeout, invalid responses into normalized exceptions for provider to wrap as ProviderError.
- Status: ✅ (provider wraps client exceptions into ProviderError; client validates JSON type)

2.3 Test-friendly design
- Keep mockable interfaces; avoid hard dependencies on global clients.
- Provide injectable httpx client for tests or dependency-injected session factory.
- Status: ✅ (OllamaClient now accepts injected AsyncClient or a client_factory; owns/does-not-own lifecycle honored to avoid double-close; enables pytest-httpx and custom transports cleanly)

## 3) Observability & Privacy

3.1 Structured logging
- Include: request_id, provider="ollama", method, path, status_code, duration_ms.
- Do not log prompts/messages/embeddings; at most sizes/counters.
- Status: IN PROGRESS (provider/client/API observability instrumentation and tests underway; provider mapping includes fields; additional client-level emitters planned if required)

3.2 Correlation propagation
- Ensure X-Request-ID is sent downstream when available.
- Status: ✅ (client forwards X-Request-ID; test added)

## 4) Documentation Updates to Complete

4.1 Feature 03 — Technical Requirements and Configuration
- Fill in explicit env var details (OLLAMA_HOST, REQUEST_TIMEOUT_S) and tracing header usage.
- Document non-streaming rejection in v1.0.
- Document router-first operation: by default, the gateway forwards requests as-is to Ollama, with progressive enrichment layers (prompt efficiency, context compression, tool routing) gated behind configuration and response_format strategies.
- Status: ✅ (docs completed in 03-Technical-Requirements-and-Configuration.md)

4.2 Feature 04 — API Mapping: List Models
- Provide example request/response; note created timestamp parsing and fallbacks.
- Status: ✅ (docs completed in 04-API-Mapping-List-Models.md)

4.3 Feature 05 — API Mapping: Embeddings
- Document batching behavior for list input; error handling policy (fail whole request for any upstream error in v1.0).
- Provide example request/response.
- Status: ✅ (docs completed in 05-API-Mapping-Embeddings.md)

4.4 Feature 07 — API Mapping: Chat Completions
- Add concrete mapping examples for response_format and options; created/usage mapping.
- Add router-first table mapping for all OpenAI fields to Ollama (or options capture) to ensure “every option and value is properly intercepted and forwarded”.
- Status: ✅ (document updated with mapping, structured responses, tasks, and acceptance criteria)

4.5 Feature 08 — Testing Strategy and QA
- Finalize uv-based commands and coverage gates; list fixtures for httpx mocking, time freezing, and id generation stubs.
- Status: ✅ (docs completed in 08-Testing-Strategy-and-QA.md)

4.6 PRD — Cross-check
- Ensure all feature pages are updated to Status: ✅ once implemented; legacy completions page remains “excluded” with rationale.
- Status: TODO

## 5) Testing

5.1 Unit tests — provider
- Chat: happy path mapping, response_format=json, options mapping, missing/invalid upstream fields → ProviderError.
- Embeddings: single and list inputs; missing embedding → ProviderError.
- Models: empty models array → empty OpenAI list; timestamp parsing (valid/invalid).
- Router parity: assert all OpenAI Chat fields are intercepted and included in mapped payload (even if not used by Ollama yet) to prove “router-first” coverage.
- Status: PARTIAL (existing tests cover core chat path; add assertions for pass-through and intercept coverage)

5.2 Unit tests — client
- httpx success/timeout/network error branches; ensure normalized exceptions.
- Request body/headers correctness; X-Request-ID forwarded when present.
- Router-first fallback: verify deterministic stubs on localhost failure for chat/tags/embeddings.
- Status: PARTIAL (header propagation test added; more httpx-transport mocks planned)
  - Next: add explicit tests for correlation header propagation and structured logging fields presence in client logs (without payload leakage).

5.3 Integration tests — core routes
- With provider wired to mocked client:
  - GET /ollama/v1/models
  - POST /ollama/v1/embeddings
  - POST /ollama/v1/chat/completions (non-streaming only)
- 401/422/502 paths via core handlers; non-streaming rejection validated.
- Status: TODO (ready to add with current provider/client)
  - Next: add API-level observability assertions: request_id present in logs, security headers retained, no secrets leaked.

5.4 Static checks & coverage
- Ensure mypy strict passes; ruff check/format clean; coverage ≥ 85% for provider logic.
- Commands:
  - uv run ruff check && uv run ruff format --check
  - uv run mypy
  - uv run pytest --maxfail=1 -q --cov=src --cov-report=term-missing
- Status: ✅ (current pipeline green; overall coverage ~90%)

## 6) Acceptance Criteria Recap (v1.0)

- Provider implements list_models, create_embeddings, chat_completions with real client mapping and robust error handling. ✅
- Router-first pass-through: all OpenAI Chat options/fields are intercepted and forwarded or captured (for future enrichment). ✅
- Non-streaming only; stream=true deterministically rejected. ✅
- OpenAI-compatible responses for all in-scope endpoints; structured responses prioritized via response_format mapping. ✅
- Structured logging with correlation id; zero leakage of sensitive payloads. IN PROGRESS (observability implementation and tests underway)
- Tests pass; coverage threshold met; static analysis clean. ✅

## 8) Work Items Selected Next (Observability Focus)

- Implement structured logging fields at provider layer (Ollama): request_id, provider, method/path, status_code, duration_ms; ensure no payload logging. Add unit tests capturing logs and asserting fields. Target ≥85% coverage for new logic.
- Client correlation propagation tests: verify X-Request-ID forwarding and absence of secrets in headers/logs. Expand pytest-httpx tests to assert headers and negative cases. Target ≥85% coverage on exercised paths.
- API-level log assertions: integration tests to ensure middleware and handlers emit structured logs with request_id and no secret leakage. Validate 401/502 error paths include required fields.

Blocking issues: None.

## 7) Future Scope (Post v1.0, not in this TODO)

- Legacy Completions endpoint support via /api/generate mapping.
- Streaming (SSE/JSON lines) support if Core enables it.
- Enhanced usage accounting if upstream begins returning token counts for embeddings.
