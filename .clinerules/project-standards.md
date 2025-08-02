# Project Standards — Universal AI Gateway

Authoritative engineering standards for the Universal AI Gateway v1.0 and future work. These specifications align with PRD-1.0 and the organization-wide Python guidelines.

## 1. Language, Runtime, and Style

- Python: 3.12+ required.
- Use uv and pyproject.toml for dependency management. Configure uv with `system = true` for Docker containers.
- Typing: strict type hints for all public functions, methods, classes, and module variables. Codebase must be mypy-clean under strict settings.
- Linting/Formatting:
  - Ruff for linting AND formatting (unified tool). Configuration in pyproject.toml only.
  - Selected rules: E, F, W, N, I, C90, UP, B, A, C4, T20, SIM
  - Complexity limit: max 10 (mccabe)
  - Line length: 100 characters
  - Pre-commit hooks mandatory: ruff check, ruff format, mypy, whitespace, EOF newline.
- Code Quality:
  - No unused code/vars; no wildcard imports.
  - No broad except clauses; catch specific exceptions.
  - Keep functions cohesive and small; cyclomatic complexity kept low (<10 enforced).
  - Docstrings for all public classes and functions (Google or NumPy style).
  - Use isort settings: known-first-party = ["ai_gateway"], combine-as-imports = true

## 2. Project Structure

```
src/ai_gateway/
  api/            # app factory, routers
  providers/      # base interface and concrete providers (custom, cerebras, ollama), client wrappers
  schemas/        # OpenAI-compatible request/response models, shared DTOs
  config/         # config.py, constants.py, __init__.py
  exceptions/     # custom error types and global exception handlers
  middleware/     # auth dependency, correlation id, security headers
  logging/        # logging setup and formatters
  utils/          # reusable helpers (mapping utils, ID generation, etc.)
tests/
  api/
  providers/
  schemas/
  config/
  exceptions/
  middleware/
  logging/
scripts/          # run scripts, docker entrypoints, utilities
.github/workflows/  # CI pipelines
docs/             # examples and additional docs (optional)
```

- Tests mirror src structure.
- Keep modules cohesive; avoid circular imports (prefer dependency injection).
- New providers must live in `providers/` and implement the base interface.

## 3. Configuration and Secrets

- Centralized configuration via `pydantic-settings` in `src/ai_gateway/config/config.py`.
- Environment variables are the single source of truth. `.env` is for local development only.
- Required environment variables (v1.0):
  - SERVICE_HOST (default: 0.0.0.0)
  - SERVICE_PORT (default: 8000)
  - LOG_LEVEL (default: INFO; values: DEBUG, INFO, WARNING, ERROR)
  - ALLOWED_API_KEYS (CSV; required in non-dev)
  - CEREBRAS_API_KEY (required if Cerebras endpoints used)
  - CEREBRAS_BASE_URL (optional; defaults per SDK)
  - OLLAMA_HOST (e.g., http://localhost:11434)
  - REQUEST_TIMEOUT_S (default: 30)
  - ENABLE_SECURITY_HEADERS (default: true)
- Constants: define in `config/constants.py` (paths, header names, provider identifiers, timeouts). Re-export via `config/__init__.py` for unified import surface.
- Do not log secrets. Redact known secret values in logs.

## 4. FastAPI Conventions

- App factory pattern: `ai_gateway.api.app.get_app()` returns a configured `FastAPI` instance.
- Routers per namespace and version:
  - `/v1/chat/completions` → Custom Processing Provider (default)
  - `/cerebras/v1/chat/completions` → Cerebras Provider
  - `/ollama/v1/chat/completions` → Ollama Provider
  - `/healthz` → readiness/health endpoint
- Dependency Injection:
  - Inject config, provider instances, and auth validation via `Depends`.
  - Providers resolved through a composition root in the app factory to allow test-time substitution.
- Pydantic models:
  - All request and response payloads use typed Pydantic models.
  - Forbid extra fields by default; validate enums and constraints.

## 5. Authentication

- Bearer token authentication via `Authorization: Bearer <API_KEY>`.
- `ALLOWED_API_KEYS` is a comma-separated list; whitespace is trimmed; case-sensitive matching.
- Failures return HTTP 401 with `WWW-Authenticate: Bearer` and standardized error payload.
- No sessions or cookies; the service is stateless.

## 6. OpenAI Compatibility Scope (v1.0)

- Supported endpoint: `POST /<namespace>/chat/completions` only.
- Request and response must match the OpenAI Chat Completions format:
  - Response must include: `id`, `object`, `created`, `model`, `choices`, `usage`.
- Out-of-scope (return 404/405 as appropriate): streaming responses, embeddings, images, audio, other OpenAI endpoints.

## 7. Provider Abstraction

- Base Interface (`providers/base.py`):
  - `class ChatProvider(Protocol):`
    - `async def chat_completions(self, req: ChatCompletionRequest) -> ChatCompletionResponse: ...`
- Implementations:
  - CustomProcessingProvider (default): logs structured input, returns deterministic mock response.
  - CerebrasProvider: maps to `cerebras.cloud.sdk` `chat.completions.create(...)`, transforms back to OpenAI schema.
  - OllamaProvider: maps to `ollama.chat(...)`, transforms back to OpenAI schema.
- Client wrappers (`cerebras_client.py`, `ollama_client.py`):
  - Encapsulate third-party SDK/client initialization, base URLs, and timeouts.
- Mapping rules:
  - Normalize roles and content.
  - Set `created` to current epoch seconds.
  - Generate `id` as `chatcmpl-<ulid/uuid>` style.
  - `object` = `chat.completion`.
  - Map `finish_reason` to OpenAI-compatible enum values.
  - Populate `usage` from provider if available; else provide conservative estimates or zeros with TODO notes.
- Error normalization:
  - Convert provider/network/timeout errors to `ProviderError` (HTTP 502).
  - Do not leak provider stack traces in API responses.

## 8. Error Handling

- Custom exception types (`exceptions/errors.py`):
  - `AuthError` → 401
  - `ValidationAppError` → 422
  - `ProviderError` → 502
  - `InternalError` → 500
- Global handlers (`exceptions/handlers.py`):
  - Register with app; return a standardized error payload:
    ```json
    {
      "error": {
        "type": "string",
        "message": "string",
        "details": { "optional": "object" }
      }
    }
    ```
- Validation errors (FastAPI/Pydantic) normalized through the global handler.
- Log errors with structured context; do not include secrets.

## 9. Middleware and Security

- Correlation ID:
  - Middleware reads `X-Request-ID` or generates a new ID; use a `contextvar` to propagate.
  - Include `request_id` in all logs and pass to providers if possible.
- Security headers (enabled by default):
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Referrer-Policy: no-referrer`
  - `Permissions-Policy: ()` or minimal safe defaults
- CORS: only enable if explicitly required; default is disabled or restricted.
- Timeouts: all outbound provider calls must have explicit timeouts from config.

## 10. Logging

- Structured logging with fields:
  - `timestamp`, `level`, `request_id`, `method`, `path`, `provider`, `status_code`, `duration_ms`, `message`
- Format: JSON or key-value; must be machine-parseable.
- Levels:
  - `INFO` for normal ops; `DEBUG` allowed in dev only.
  - `WARNING` for recoverable anomalies; `ERROR` for failures with tracebacks.
- No logging of secrets; redact tokens and keys.

## 11. Testing and TDD

- Testing framework: `pytest` with `pytest-asyncio`.
- Coverage target: ≥ 85–90% for business logic; enforce via CI.
- Test categories:
  - Unit tests for models, config, utilities, and provider mapping (with mocks).
  - API integration tests using `httpx.AsyncClient` against app factory.
  - Error path tests for auth, validation, provider failures.
- External SDKs and services must be mocked; no real calls in CI.
- Test structure mirrors `src/` packages.

## 12. Performance and Concurrency

- All provider calls are async and non-blocking.
- Configure request timeouts; consider retry with backoff for transient errors (opt-in, not default).
- Avoid CPU-bound tasks on the request path; if needed, offload to background tasks or workers (future scope).

## 13. Versioning and API Stability

- Versioned routes:
  - `/v1/` (custom processing default)
  - `/cerebras/v1/`
  - `/ollama/v1/`
- Breaking API changes require a new versioned route.
- Document supported models/providers per release in README.

## 14. Dependency Management

- Manage dependencies in `pyproject.toml`; pin major versions.
- Use uv with `system = true` for Docker container deployments.
- Minimize dependencies; periodically update with CI verification.
- Use uv lock files for reproducible builds.
- All tool configurations (ruff, mypy, pytest) must be in pyproject.toml - no separate config files.

## 15. Deployment and Operations

- Stateless service; horizontally scalable.
- Health endpoint: `/healthz` returns `200 OK` with minimal body.
- Docker:
  - Multi-stage build; non-root runtime user.
  - Healthcheck using `/healthz`.
  - Readiness/liveness probes configured by platform.
- Configuration via environment variables; secrets injected via platform secret manager.

## 16. Documentation

- README:
  - Setup steps, environment variables, local run instructions.
  - cURL examples for `/v1/chat/completions`, `/cerebras/v1/chat/completions`, `/ollama/v1/chat/completions`.
- `.env.example` listing all variables with comments.
- PRD retained in repo (`PRD-1.0.md`).
- Maintain `CHANGELOG.md` per release.
- Public APIs and critical modules have docstrings and usage notes.

## 18. Tool Configuration Standards

- **Single Source**: All tool configurations must be in `pyproject.toml`. No separate config files (ruff.toml, mypy.ini, etc).
- **Ruff Configuration**:
  - target-version = "py312", line-length = 100
  - Selected rules: E, F, W, N, I, C90, UP, B, A, C4, T20, SIM
  - mccabe max-complexity = 10
  - isort: known-first-party = ["ai_gateway"], combine-as-imports = true
  - Allow broad Exception in tests (B017), allow print statements (T201)
  - Use modern Python syntax: `X | None` over `Optional[X]`, `list[X]` over `List[X]`
- **MyPy Configuration**:
  - strict = true, python_version = "3.12"
  - mypy_path = "src", show_error_codes = true
  - warn_unused_ignores, warn_redundant_casts, disallow_untyped_defs
  - Tests: disallow_untyped_defs = false (override)
- **Pytest Configuration**:
  - asyncio_mode = "auto", testpaths = ["tests"]
  - Coverage: --cov=src --cov-report=term-missing
- **UV Configuration**:
  - system = true (for Docker containers, no venv)

## 17. Acceptance Criteria for v1.0

- Endpoints implemented and authenticated:
  - `/v1/chat/completions` (CustomProcessingProvider)
  - `/cerebras/v1/chat/completions` (CerebrasProvider)
  - `/ollama/v1/chat/completions` (OllamaProvider)
  - `/healthz`
- Responses conform to OpenAI Chat Completions schema.
- CI green: lint, type-check, tests, coverage threshold met.
- No secret leakage in logs; security headers enabled (if configured).
- Structured logging with correlation ID in place.
