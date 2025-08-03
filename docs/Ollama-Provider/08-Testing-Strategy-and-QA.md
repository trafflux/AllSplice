# Feature 08 — Testing Strategy and QA for Ollama Provider

Status: ✅ Complete

Purpose:
Define a comprehensive, TDD-focused testing and QA plan for the Ollama provider module, aligned with the Core OpenAI Endpoint Layer and org standards (mypy, ruff, coverage ≥ 85%). Ensure mappings, error normalization, and non-streaming behavior are verifiable and stable.

Outcomes:
- Clear test categories and fixtures for provider unit tests and core integration tests.
- Mocking strategy for Ollama HTTP calls with deterministic behaviors (success, timeouts, malformed).
- CI-ready expectations tied to uv and pytest invocations.

Scope:
- Provider-level unit tests (HTTP client mocked; no real network).
- Core integration tests using the app factory and provider injection to assert OpenAI schema conformance through routes.
- Static analysis and formatting gates (mypy, ruff).

Core Alignment:
- Transport/auth/validation tested at the core level; provider tests focus on mapping and normalization.
- Errors raised by provider as `ProviderError` are normalized by core handlers to HTTP 502.
- Non-streaming default for v1 must be enforced consistently with core features (09/10).

Test Categories:
1. Unit Tests — List Models
   - Success mapping: `/api/tags` → OpenAI ListModels.
   - Empty `models` array → OpenAI list with empty `data`.
   - Invalid/missing `modified_at` → created fallback to current epoch with warning logged.
   - Timeout/network errors (httpx.ReadTimeout, HTTP 5xx) → `ProviderError`.

2. Unit Tests — Embeddings
   - Single input string maps to `data[0]` with `object="embedding"`, `index=0`.
   - List input behavior: sequential per-item POSTs, aggregated `data[i]` with preserved ordering.
   - Missing `embedding` → `ProviderError` except when localhost deterministic fallback path is active.
   - Usage zeros present; model mapped; created parsed when present.

3. Unit Tests — Chat Completions
   - Messages passed through; response mapped to `choices[0].message`.
   - response_format `{type: "json_object"}` → `format: "json"` and `options.structured=true`.
   - Options pass-through parity: temperature, top_p, top_k, presence_penalty, frequency_penalty, stop, seed, max_tokens→num_predict, logprobs, logit_bias, n, user, tools, tool_choice.
   - Streaming request rejected with `ProviderError`.
   - Token usage fields mapped with fallbacks to 0.

4. Integration Tests with Core
   - Exercise core routes:
     - GET `/{provider}/v1/models`
     - POST `/{provider}/v1/embeddings`
     - POST `/{provider}/v1/chat/completions`
   - Assert OpenAI schema shapes and HTTP codes; 401, 422, 502 paths verified.
   - Verify `WWW-Authenticate: Bearer` on 401.

5. Observability & Redaction Tests
   - Logs contain `request_id`, provider, method, path, status_code, duration_ms.
   - Ensure prompts/messages/embeddings are not logged; only lengths/counters if needed.
   - Header propagation: `X-Request-ID` forwarded downstream in client calls.

Fixtures and Mocks:
- pytest-httpx for httpx transport mocking with:
  - success JSON, HTTP 5xx errors, and timeouts via callbacks raising `httpx.ReadTimeout`.
- Builders for OpenAI typed models per endpoint.
- Time control for deterministic `created` timestamps (freeze time or patch converter).
- UUID/ULID stub for stable `id` values in chat responses.
- Log capture fixture asserting structured fields and redaction.

Error Normalization Assertions:
- Provider raises `ProviderError` with sanitized message; no upstream details in exception text.
- Core handler converts `ProviderError` to HTTP 502 with standardized payload (tested in integration).

Coverage & Static Checks:
- Coverage target: ≥ 85% for provider logic; current project ≈ 90%.
- Commands:
  - Plain pytest:
    - pytest --maxfail=1 -q --cov=src --cov-report=term-missing
  - With uv:
    - uv run pytest --maxfail=1 -q --cov=src --cov-report=term-missing
  - Lint/format:
    - uv run ruff check && uv run ruff format --check
  - Type-check:
    - uv run mypy

Tasks (Completed):
1. Establish Provider Unit Test Suite Skeleton
   - Parametrized tests per endpoint mapping; reusable HTTP mock and time utilities.

2. Add Core Integration Tests
   - Provider wired in app factory DI; schema paths verified including error codes.

3. Logging & Privacy Checks
   - Structured logs and redaction asserted in provider/client/API layers.

4. CI/Commands Documentation
   - uv and plain pytest command examples included above.

Acceptance Criteria:
- Tests cover success and error branches for all in-scope mappings.
- Integration tests confirm OpenAI schema compliance end-to-end.
- Static checks pass (mypy/ruff); coverage ≥ 85% on provider logic.
- Logs verified for required fields and redaction policy.

Review Checklist:
- Error paths adequately tested for network, timeouts, malformed JSON.
- Non-streaming behavior matches core policy.
- Schema compliance verified at provider and core integration layers.
