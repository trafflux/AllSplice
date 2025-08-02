# Phase 4 — App Factory, Routers, and Error Handling

Authoritative source: .clinerules/project-standards.md. Implement FastAPI app factory, versioned routers, auth wiring, global exceptions, healthz, and basic OpenAI-compatible skeleton responses where necessary. Strict typing, mypy-clean, Ruff, pytest.

## 4.1 App Factory and Composition Root

- [x] 4.1.1 Implement app factory (src/ai_gateway/api/app.py)
  - get_app() -> FastAPI with:
    - Global exception handlers registered (implemented in exceptions/handlers.py and wired)
    - Middleware placeholders (correlation ID, security headers) TODO stubs
    - Routers mounted: /v1, /cerebras/v1, /ollama/v1, and /healthz
    - Dependency injection of settings/providers via composition root (initial wiring; providers in 4.4.x)
  - Configurable CORS disabled by default per standards
  - Notes: App factory present and used by tests; handlers are registered globally in app factory per Project Standards.

- [~] 4.1.2 Unit tests for app factory (tests/api/test_app.py)
  - App instantiation succeeds
  - Routers included, healthz returns 200
  - Notes: Health and router assertions currently live in tests/api/test_routes.py. A dedicated test_app.py file is not present; coverage is effectively provided via integration tests. Add minimal unit test file for explicit app factory checks. [BLOCKER: CI coverage risk if required by checklist]

## 4.2 Routers and Endpoints (updated)

- [x] 4.2.1 Define routers module (src/ai_gateway/api/routes.py)
  - Router: /healthz (GET) → 200 {"status": "ok"} [Implemented]
  - Router: /v1/chat/completions (POST) → uses CustomProcessingProvider (deterministic) [Implemented]
  - Router: /cerebras/v1/chat/completions (POST) → wired to CerebrasProvider [Implemented in Phase 6]
  - Router: /ollama/v1/chat/completions (POST) → currently wired to OllamaProvider module exists; verify behavior [In progress in later phases]
  - All chat endpoints behind Depends(auth_bearer) [Implemented]

- [~] 4.2.2 Integration tests (tests/api/test_routes.py)
  - /healthz returns 200 [Present]
  - /v1/chat/completions requires auth → 401 without, 200 with valid key (mock provider) [Present; fragile due to settings DI]
  - /cerebras endpoint now functional, not 501 → tests should assert 200 on success path (with mock) and standardized error payloads on failures [Pending]
  - /ollama endpoint present; tests to be adjusted per provider status [Pending]
  - Notes: Update tests to reflect standardized error payload {"error": {...}} and WWW-Authenticate on 401. [BLOCKER: CI failures until assertions updated]

## 4.3 Global Exceptions

- [x] 4.3.1 Implement exceptions/errors.py and exceptions/handlers.py
  - Define AuthError, ValidationAppError, ProviderError, InternalError [Implemented]
  - Global handlers return standardized payload:
    {
      "error": { "type": "string", "message": "string", "details": { ... } }
    } [Implemented]
  - Normalize HTTPException vs custom exceptions; ensure WWW-Authenticate for 401 from auth path if needed [Implemented]
  - Notes: Handlers registered in app factory. Tests and routes must assert standardized shape.

- [ ] 4.3.2 Tests for exception handlers (tests/exceptions/test_handlers.py)
  - Simulate raising each error via a test route; assert status and response schema
  - Notes: Handler-specific tests not yet present; behavior indirectly covered via middleware/api tests but needs dedicated coverage. [BLOCKER: coverage gap if required by standards]

## 4.4 Minimal CustomProcessingProvider (default path)

- [x] 4.4.1 Provider interface and minimal implementation
  - providers/base.py: ChatProvider Protocol [Implemented]
  - providers/custom.py: CustomProcessingProvider returning deterministic mock response in OpenAI schema (id, object, created, model, choices, usage) [Implemented]
  - Ensure mapping helpers adhere to standards (created epoch, id format, object name) [Implemented]

- [x] 4.4.2 Tests for provider mapping (tests/providers/test_custom.py)
  - Validate response fields and enums; usage defaults present [Implemented]
  - Notes: Deterministic behavior verified in tests.

## 4.5 Config and Constants usage

- [~] 4.5.1 Validate config wiring in app factory
  - Ensure settings usage consistent and no secrets in logs [In progress; current usage conforms]
  - Constants for paths used from config/constants.py [Implemented]
  - Notes: Settings DI currently reconstructed in some dependencies (auth); future composition root to centralize and reduce test fragility. Add a quick audit to confirm no secret logging. [BLOCKER: None runtime; CI stability risk]

## 4.6 Lint/Type/Test

- [~] 4.6.1 Resolve current diagnostics
  - Clean up remaining pylance/mypy issues in middleware tests and auth [In progress]
  - Ensure mypy strict passes [Generally passing; re-verify after recent changes]

- [~] 4.6.2 Run pytest with coverage
  - Ensure all added tests pass, maintain structure and coverage expectations [Coverage ~86% when stable]
  - Notes: Intermittent failures caused by settings DI in tests; update tests and DI to stabilize coverage. [BLOCKER: CI coverage flakiness]

## Acceptance Criteria

- get_app() returns a configured FastAPI instance with mounted routers and global handlers. [Met]
- /healthz returns 200 OK. [Met]
- /v1/chat/completions requires auth and returns a deterministic mock response in OpenAI schema. [Met]
- /cerebras endpoint is functional via CerebrasProvider; /ollama path exists with provider scaffold. [Updated]
- Standardized error schema implemented for errors, 401 path maintains WWW-Authenticate header. [Met]
- Mypy strict and Ruff clean; pytest suite passes locally. [Partially met due to DI/test fragility]
