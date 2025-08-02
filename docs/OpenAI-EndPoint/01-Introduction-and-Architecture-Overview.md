# Feature 01 — Introduction and Architecture Overview

Status: ⚠️ Incomplete

Purpose:
Establish the high-level architecture and guiding principles for the Core OpenAI Endpoint Layer that is provider-agnostic, reusable, and compliant with OpenAI REST API standards. This feature aligns the project with the PRD’s modular goals and sets the foundation for subsequent endpoint and provider work.

Outcomes:
- Clear architectural diagram and narrative describing API layer, routing, provider abstraction, schemas, middleware, and error handling.
- Defined boundaries: in-scope behaviors for this layer vs. out-of-scope provider-specific logic.
- Shared terminology and conventions to be used across all features.

Tasks:
1. Architecture Narrative and Diagrams — ⚠️
   - Architecture description:
     - Public API layer (FastAPI app factory, routers).
       - App factory: ai_gateway.api.app.get_app() composes middleware, exception handlers, logging, and router registration.
       - Routers expose OpenAI-compatible endpoints under a versioned, provider-first namespace pattern: /{provider}/v1/...
     - Routing mechanism using provider namespace segment: /{provider}/v1/... with fixed version segment v1. See Feature 05 for resolution details.
     - Provider abstraction (base interface and provider resolution).
       - ChatProvider-style Protocol for v1 methods; concrete providers bound via composition root (config-driven).
     - Schemas (OpenAI-compatible request/response).
       - Pydantic models under src/ai_gateway/schemas/* with extra="forbid" to reject unknown fields.
     - Middleware (auth, correlation ID, security headers, structured logging).
       - Auth validates Authorization: Bearer against ALLOWED_API_KEYS.
       - Correlation middleware extracts/generates X-Request-ID and propagates via contextvars.
       - Security headers added when ENABLE_SECURITY_HEADERS=true.
       - Logging middleware emits structured logs with request_id, provider, method, path, status_code, duration_ms.
     - Exceptions and global error normalization.
       - Custom exceptions mapped to HTTP codes via global handlers; provider/internal errors normalized to ProviderError → 502.
     - Configuration via pydantic-settings and environment variables.
       - Centralized settings in ai_gateway.config.config with constants in ai_gateway.config.constants.
   - High-level diagram (Mermaid):

     ```mermaid
     flowchart LR
       Client -->|HTTP| FastAPI[API Layer (Routers)]
       FastAPI -->|Auth, CorrID, Sec Headers, Logging| Middleware
       FastAPI -->|Parse+Validate (Pydantic)| Schemas
       FastAPI -->|Resolve provider via DI| Resolver[Provider Registry]
       Resolver --> Provider[Provider Interface (v1)]
       Provider -->|Async calls| ExternalSDK[(Provider SDK / HTTP)]
       FastAPI --> Handlers[Global Exception Handlers]
       Handlers --> Client
       subgraph Config
         Settings[pydantic-settings]
         Constants[constants.py]
       end
       Config --> FastAPI
       Config --> Resolver
     ```

   - Status: ⚠️

2. Provider-Agnostic Design Principles — ⚠️
   - Endpoints are transport-only: parse, validate, dispatch; no provider-specific branching.
   - Extension strategy:
     - Implement the v1 provider Protocol in a new module.
     - Register/bind via configuration in the app factory (composition root).
     - No changes required in routers or core API to add a provider.
   - Future endpoints (images, audio) follow same pattern:
     - Add schemas, add routers, extend base interface or compose new interfaces; bind via DI.

3. Compliance Scope with OpenAI REST — ⚠️
   - Supported for v1:
     - GET /{provider}/v1/models
     - POST /{provider}/v1/embeddings
     - POST /{provider}/v1/completions (legacy)
     - POST /{provider}/v1/chat/completions
   - Inputs/outputs validated/shaped to OpenAI schemas, with normalization of ids, objects, created, choices, finish_reason, and usage.

4. Operational Considerations — ⚠️
   - Stateless service; horizontally scalable.
   - Async, non-blocking provider calls with explicit timeouts (REQUEST_TIMEOUT_S).
   - Health/readiness endpoint referenced; may be outside this feature’s scope but assumed present for ops.

5. Standards and Constraints Alignment — ⚠️
   - Python 3.12+, strict type hints, mypy strict, Ruff lint/format, line length 100, cyclomatic complexity ≤ 10.
   - TDD-first with pytest, pytest-asyncio, coverage ≥ 85% for business logic.
   - Configuration and tooling consolidated in pyproject.toml; uv for package and execution.

Acceptance Criteria:
- A documented architecture overview exists with clear component boundaries and data flow.
- The provider-agnostic strategy is explained and testable by substituting providers.
- OpenAI endpoint compatibility scope is explicitly listed.
- Constraints (typing, linting, TDD) acknowledged with traceability to standards.

Test & Coverage Targets:
- Documentation-only feature: verified via downstream integration tests of app factory, routers, DI; overall coverage ≥ 85% targeted across features.

Review Checklist:
- Does the overview prevent coupling between endpoints and provider specifics?
- Are future endpoints easily accommodated by the described architecture?
- Are responsibilities and boundaries clear to contributors?

Dependencies:
- Project-wide standards and configurations (pyproject.toml, pydantic settings).
- Provider base interface (Feature 04).
- Routing design (Feature 05).
- Middleware features (auth, correlation ID, security headers) from global standards.

Acceptance Criteria:
- A documented architecture overview exists with clear component boundaries and data flow.
- The provider-agnostic strategy is explained and testable by substituting providers.
- OpenAI endpoint compatibility scope is explicitly listed.
- Constraints (typing, linting, TDD) are acknowledged with traceability to standards.

Test & Coverage Targets:
- Documentation-only feature: tests are covered by downstream features that validate the architecture via integration tests (app factory, routers, DI). Aim to ensure subsequent features collectively keep overall coverage ≥ 85%.

Review Checklist:
- Does the overview prevent coupling between endpoints and provider specifics?
- Are future endpoints easily accommodated by the described architecture?
- Are responsibilities and boundaries clear to contributors?
