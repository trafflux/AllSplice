# Feature 08 — Testing Strategy and QA for Ollama Provider

Status: ⚠️ Incomplete

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
   - Invalid/missing `modified_at` → created=0 with warning logged.
   - Timeout/network errors → `ProviderError`.
   - Status: ⚠️

2. Unit Tests — Embeddings
   - Single input string maps to `data[0]` with `object="embedding"`, `index=0`.
   - List input behavior:
     - If Strategy B chosen: multiple calls aggregated into `data[i]`.
     - If Strategy A chosen: deterministic documented failure/limitation.
   - Missing `embedding` → `ProviderError`.
   - Usage zeros present; model mapped.
   - Status: ⚠️

3. Unit Tests — Completions (Legacy)
   - Request options mapping: max_tokens→num_predict, stop, temperature, top_p, seed.
   - Response mapping to OpenAI (id/object/created/choices/usage).
   - `done`/`done_reason` → finish_reason normalization.
   - Streaming request:
     - Behavior consistent with core policy (error or force non-streaming).
   - Timeout/HTTP errors and malformed responses → `ProviderError`.
   - Status: ⚠️

4. Unit Tests — Chat Completions
   - Messages passed through; response mapped to `choices[0].message`.
   - response_format `{type: "json_object"}` → `format: "json"`, else omit.
   - Options mapping identical to completions for generation params.
   - Streaming request behavior consistent with core.
   - Token usage fields mapped; fallbacks to 0 when absent.
   - Status: ⚠️

5. Integration Tests with Core
   - Wire Ollama provider mock via DI in app factory.
   - Exercise core routes:
     - GET `/{provider}/v1/models`
     - POST `/{provider}/v1/embeddings`
     - POST `/{provider}/v1/completions`
     - POST `/{provider}/v1/chat/completions`
   - Assert OpenAI schema shapes and HTTP codes; 401, 404, 422, 502 paths verified.
   - Status: ⚠️

6. Observability & Redaction Tests
   - Logs contain `request_id`, provider, method, path, status_code, duration_ms.
   - Ensure prompts/messages/embeddings are not logged; only lengths/counters if needed.
   - Status: ⚠️

Fixtures and Mocks:
- Async HTTP client mock with parametrized responses for success/error/timeouts.
- Request builders for OpenAI typed models per endpoint.
- Time control for deterministic `created` timestamps (freeze time or stub conversion).
- ULID/UUID generation stub to produce stable `id` for assertions.

Error Normalization Assertions:
- Provider raises `ProviderError` with sanitized message; no upstream details in exception text.
- Core handler converts `ProviderError` to HTTP 502 with standardized payload (tested in integration).

Coverage & Static Checks:
- Coverage target: ≥ 85% for provider logic; aim ≥ 90% for mappings.
- Run with:
  - `uv run pytest --maxfail=1 -q --cov=src --cov-report=term-missing`
- MyPy and Ruff:
  - `uv run mypy`
  - `uv run ruff check && uv run ruff format --check`
- Pre-commit: ensure hooks cover ruff, mypy, eof, whitespace.

Tasks:
1. Establish Provider Unit Test Suite Skeleton
   - Create parametrized tests per endpoint mapping.
   - Implement reusable HTTP mock and time utilities.
   - Status: ⚠️

2. Add Core Integration Tests
   - Substitute provider with a mock implementation in DI for app factory.
   - Validate transport-level behavior (auth/validation handled by core).
   - Status: ⚠️

3. Logging & Privacy Checks
   - Assert structured logs and redaction.
   - Status: ⚠️

4. CI/Commands Documentation
   - Provide uv-based commands for local and CI runs.
   - Status: ⚠️

Acceptance Criteria:
- Tests cover success and error branches for all four mappings.
- Integration tests confirm OpenAI schema compliance end-to-end (with provider mocks).
- Static checks pass (mypy/ruff); coverage ≥ 85% on provider logic.
- Logs verified for required fields and redaction policy.

Review Checklist:
- Are error paths adequately tested for network, timeouts, malformed JSON?
- Do tests ensure non-streaming behavior matches core policy?
- Is schema compliance verified at both provider and core integration layers?
