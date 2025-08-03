# Universal AI Gateway v1.0 — Engineering Task Breakdown

This checklist implements PRD-1.0 using Python 3.12+, FastAPI, and TDD with pytest. All tasks presume strict typing, DI, structured logging, and security per standards.

## Phase 0 — Repo Scaffolding and CI/CD

- [x] 0.1 Create directories
  - [x] src/ai_gateway/{api,providers,schemas,config,exceptions,logging,middleware,utils}
  - [x] tests/{api,providers,schemas,config,exceptions,logging,middleware,utils}
  - [x] scripts, docs
  - [x] .github/workflows
- [ ] 0.2 Add pyproject.toml with dependencies
  - Runtime: fastapi, uvicorn[standard], pydantic, pydantic-settings, httpx, python-dotenv, anyio, typing-extensions, cerebras-cloud-sdk, ollama
  - Dev: pytest, pytest-asyncio, pytest-cov, ruff, mypy, ruff-format or black, types-requests
  - Note: Partial. Standards gaps: single-source configuration required in pyproject.toml; repository currently has pytest.ini and pyrightconfig.json. Move pytest and mypy configs into pyproject.toml, remove pytest.ini, add mypy strict block. Ensure Ruff is the formatter (ruff format)
- [ ] 0.3 Configure tooling
  - [ ] ruff.toml (lint + format rules)
  - [ ] mypy.ini (strict)
  - [ ] pytest.ini (asyncio mode, testpaths)
  - [x] pre-commit with ruff, format, mypy, end-of-file-fixer, trailing-whitespace
  - Note: Partial. Standards require all tool configs in pyproject.toml (no separate ruff.toml/mypy.ini/pytest.ini). Update pre-commit to use ruff format (not black) and ensure hooks align.
- [ ] 0.4 CI workflow
  - [x] .github/workflows/ci.yml runs: ruff, mypy, pytest (coverage threshold ≥ 85% business logic)
- [x] 0.5 Makefile
  - [x] lint, format, type, test, test-cov, run
  - Note: Partial. Verify lint uses ruff check, format uses ruff format, type uses mypy strict, test-cov enforces threshold, run uses uvicorn ai_gateway.api.app:get_app with SERVICE_PORT. Update if mismatched.

## Phase 1 — Configuration and Constants

- [ ] 1.1 Centralized configuration (pydantic-settings)
  - [x] src/ai_gateway/config/config.py
  - Env: SERVICE_HOST, SERVICE_PORT, LOG_LEVEL, ALLOWED_API_KEYS (CSV), CEREBRAS_API_KEY, CEREBRAS_BASE_URL, OLLAMA_HOST, REQUEST_TIMEOUT_S, ENABLE_SECURITY_HEADERS
  - Note: Partial. Verify REQUEST_TIMEOUT_S and ENABLE_SECURITY_HEADERS are present with defaults and strict typing; ensure mypy-clean and no secret logging.
- [x] 1.2 Constants
  - [x] src/ai_gateway/config/constants.py (API paths, headers, defaults, provider names)
  - [x] Re-export constants via config/__init__.py
  - Note: Partial. Confirm all required constants exist (Authorization, WWW-Authenticate: Bearer, X-Request-ID, API paths) and are used consistently.
- [x] 1.3 Tests
  - [x] tests/config/test_config.py (env parsing, defaults, CSV parsing, validation on required secrets)
  - Note: Partial. Ensure coverage includes CSV trimming for ALLOWED_API_KEYS, defaults for all fields (including REQUEST_TIMEOUT_S, ENABLE_SECURITY_HEADERS), and required secret validation when providers enabled.

## Phase 2 — OpenAI Chat Completions Schemas

- [x] 2.1 Request/Response Models (Pydantic)
  - [x] Enums: Role, FinishReason
  - [x] Request: ChatMessage, ChatCompletionRequest (model, messages, temperature?, max_tokens?, top_p?, stop?, user?)
  - [x] Response: ChatCompletionMessage, ChatCompletionChoice, ChatCompletionUsage, ChatCompletionResponse
  - [x] Strict validation (forbid extra, constrained types)
  - Note: Partial. Confirm models forbid extra by default and types are constrained; ensure mypy-clean; ensure created timestamps and object fields are handled downstream per standards.
- [x] 2.2 Tests
  - [x] tests/schemas/test_openai_models.py (valid/invalid payloads, enum validation, missing fields)
  - Note: Present as tests/schemas/test_openai_chat.py. Ensure test coverage includes extra fields rejection and edge cases.

## Phase 3 — Authentication Dependency

- [ ] 3.1 Bearer token auth
  - [ ] src/ai_gateway/middleware/auth.py (parse Authorization: Bearer > validate against ALLOWED_API_KEYS)
  - [ ] WWW-Authenticate: Bearer on failures
  - Note: Not started. Implement strict typing, no secret logging, CSV parsing with whitespace trimming.
- [ ] 3.2 Wiring dependency into routers with Depends
  - Note: Not started. Add Depends(auth) to chat routes.
- [ ] 3.3 Tests
  - [ ] tests/middleware/test_auth.py (missing/malformed/invalid/valid tokens, multi-key support)
  - Note: Not started.

## Phase 4 — App Factory, Routers, Provider Abstraction

- [ ] 4.1 Provider interface
  - [ ] src/ai_gateway/providers/base.py (Protocol/ABC): `async def chat_completions(req) -> ChatCompletionResponse`
  - Note: Not started.
- [ ] 4.2 Routers
  - [ ] src/ai_gateway/api/routes.py:
    - [ ] POST /v1/chat/completions -> CustomProcessingProvider
    - [ ] POST /cerebras/v1/chat/completions -> CerebrasProvider
    - [ ] POST /ollama/v1/chat/completions -> OllamaProvider
    - [ ] GET /healthz
  - Note: Not started.
- [ ] 4.3 App factory
  - [ ] src/ai_gateway/api/app.py: get_app() registers routers, middleware, exception handlers
  - Note: Not started.
- [ ] 4.4 Tests
  - [ ] tests/api/test_routes.py (routing correctness, OpenAPI schema, dependencies invoked)
  - Note: Not started.

## Phase 5 — Custom Processing Provider (Default /v1)

- [ ] 5.1 Implementation
  - [ ] src/ai_gateway/providers/custom.py: log structured request; deterministic mock OpenAI response
  - Note: Not started.
- [ ] 5.2 Tests
  - [ ] tests/providers/test_custom.py (valid shape, deterministic content, logging called)
  - Note: Not started.

## Phase 6 — Cerebras Integration

- [ ] 6.1 Client wrapper
  - [ ] src/ai_gateway/providers/cerebras_client.py: init with CEREBRAS_API_KEY/CEREBRAS_BASE_URL; timeouts
- [ ] 6.2 Provider implementation
  - [ ] src/ai_gateway/providers/cerebras.py: map OpenAI request -> cerebras.cloud.sdk chat.completions.create(); transform response -> OpenAI schema
- [ ] 6.3 Error handling
  - [ ] Normalize SDK errors/timeouts -> ProviderError(502)
- [ ] 6.4 Tests
  - [ ] tests/providers/test_cerebras.py (mock SDK; mapping fidelity; error paths)
  - Note: Not started (all items above missing).

## Phase 7 — Ollama Integration

- [ ] 7.1 Client wrapper
  - [ ] src/ai_gateway/providers/ollama_client.py: OLLAMA_HOST; async calls; timeouts
- [ ] 7.2 Provider implementation
  - [ ] src/ai_gateway/providers/ollama.py: map request -> ollama.chat(); transform to OpenAI response
- [ ] 7.3 Error handling
  - [ ] Normalize errors/timeouts -> ProviderError(502)
- [ ] 7.4 Tests
  - [ ] tests/providers/test_ollama.py (mock client; mapping; errors)
  - Note: Not started (all items above missing).

## Phase 8 — Exceptions and Global Handlers

- [ ] 8.1 Custom exceptions
  - [ ] src/ai_gateway/exceptions/errors.py: AuthError(401), ValidationAppError(422), ProviderError(502), InternalError(500)
  - Note: Partial. exceptions/ exists but errors.py not confirmed; implement with strict typing and mapping.
- [ ] 8.2 Global handlers
  - [ ] src/ai_gateway/exceptions/handlers.py: register handlers; standardized error schema
  - Note: Not started.
- [ ] 8.3 Tests
  - [ ] tests/exceptions/test_handlers.py (status codes, payload structure)
  - Note: Not started.

## Phase 9 — Middleware: Security and Correlation

- [ ] 9.1 Correlation ID
  - [ ] src/ai_gateway/middleware/correlation.py: request_id from X-Request-ID or generated; contextvar
  - Note: Not started.
- [ ] 9.2 Security headers
  - [ ] src/ai_gateway/middleware/security.py: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy
  - Note: Not started.
- [ ] 9.3 Tests
  - [ ] tests/middleware/test_correlation.py and test_security.py
  - Note: Not started.

## Phase 10 — Logging

- [ ] 10.1 Setup
  - [ ] src/ai_gateway/logging/setup.py: structured formatter (timestamp, level, request_id, method, path, provider, status_code, duration_ms)
  - Note: Partial. logging/ exists but setup.py not confirmed.
- [ ] 10.2 Integration
  - [ ] Configure level via config.LOG_LEVEL
  - Note: Not started.
- [ ] 10.3 Tests
  - [ ] tests/logging/test_logging.py (fields emitted, levels)
  - Note: Not started.

## Phase 11 — API Integration Tests and Coverage

- [ ] 11.1 Integration tests with httpx AsyncClient
  - [ ] tests/api/test_chat_completions.py: auth fail, success for each route, validation 422, provider error 502
  - Note: Not started.
- [ ] 11.2 Coverage enforcement
  - [ ] Configure pytest-cov threshold (≥ 85–90% business logic)
  - Note: Partial. pytest.ini exists; move pytest config to pyproject.toml with coverage threshold and enforce in CI.

## Phase 12 — Run and Containerization

- [ ] 12.1 Local run
  - [ ] Make run -> uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port $SERVICE_PORT
  - Note: Partial. Makefile and scripts/run_dev.sh exist; verify run target matches exactly.
- [ ] 12.2 Docker
  - [ ] Dockerfile (multi-stage), non-root user, healthcheck
  - [ ] Optional docker-compose.override.yml for local services
  - Note: Not started.
- [ ] 12.3 Smoke test
  - [ ] Build and run container; hit /healthz and sample endpoint
  - Note: Not started.

## Phase 13 — Documentation and Examples

- [ ] 13.1 README.md
  - [ ] Setup, environment variables, run instructions, curl examples for all three routes
  - Note: Partial. README.md exists; examples and full instructions pending until routes implemented.
- [ ] 13.2 .env.example
  - [ ] All keys with comments and safe defaults
  - Note: Partial. Ensure REQUEST_TIMEOUT_S and ENABLE_SECURITY_HEADERS present with comments/safe defaults.
- [ ] 13.3 Examples
  - [ ] docs/examples/*.json; scripts/curl/*.sh (sample requests/responses)
  - Note: Not started.

## Phase 14 — Release Checklist

- [ ] CI green; mypy/ruff clean; coverage met
- [ ] Tag v1.0.0; update CHANGELOG.md
- [ ] Confirm in-scope endpoints only; streaming and other OpenAI endpoints out-of-scope
  - Note: Not started. Depends on CI setup and full feature completion.
