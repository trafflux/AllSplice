# Feature 05 — Routing and Namespace Resolution

Status: ⚠️ Incomplete

Purpose:
Design and specify the routing mechanism that dispatches incoming requests by provider namespace segment `/{provider}/v1/...` to the appropriate provider implementation via dependency injection. Ensure clean separation between transport (FastAPI) and provider logic.

Outcomes:
- Deterministic routing strategy using path params for `provider` and `version`.
- Composition root that binds provider implementations from configuration.
- Consistent error paths and HTTP status codes for unknown providers and invalid routes.

Scope:
- Applies to endpoints:
  - GET `/{provider}/v1/models`
  - POST `/{provider}/v1/embeddings`
  - POST `/{provider}/v1/completions`
  - POST `/{provider}/v1/chat/completions`
- Provider resolution and injection across all routes.
- Centralized error handling handoff to global handlers.

Tasks:
1. Namespace and Version Parsing
   - Specify path parameters: `provider: str`, fixed `v1` segment for version routing.
   - Define behavior for unknown versions (404 or 405 per FastAPI routing).
   - Status: ⚠️

2. Provider Resolution Strategy
   - Document provider registry concept (mapping provider name → implementation).
   - Define resolution failure behavior: return normalized error (e.g., 404 with standardized payload).
   - Ensure resolution receives context (request_id/correlation).
   - Status: ⚠️

3. Dependency Injection (Composition Root)
   - Define how app factory wires providers from environment/config.
   - Allow test-time substitution via fixtures/mocks without code changes.
   - Status: ⚠️

4. Route Handlers (Transport-Only Responsibilities)
   - Parse path and body, validate with Pydantic schemas.
   - Call provider method; do not embed provider-specific branching.
   - Return response that matches OpenAI schema; errors delegated to global handlers.
   - Status: ⚠️

5. Error Paths and HTTP Codes
   - Unknown provider → 404 with standardized error payload.
   - Validation errors → 422 normalized via global handler.
   - Provider errors → 502 via `ProviderError`.
   - Auth failures → 401 with `WWW-Authenticate: Bearer`.
   - Status: ⚠️

6. Observability Hooks
   - Ensure structured logs include: request_id, provider, method, path, status_code, duration_ms.
   - Include provider name in logs for disambiguation across namespaces.
   - Status: ⚠️

Dependencies:
- Feature 01 — Architecture overview.
- Feature 04 — Provider interface.
- Global middleware and exception handlers from project standards.

Acceptance Criteria:
- Routing design documented with provider and version segments.
- Provider resolution defined with error semantics for unknown providers.
- DI approach enables swapping providers in tests without core changes.
- Logging fields and error code mappings are enumerated.

Test & Coverage Targets:
- Route integration tests per endpoint path confirming provider dispatch is invoked.
- Unknown provider returns 404 with standardized error payload.
- Validation failures and provider exceptions route through global handlers.

Review Checklist:
- Does routing avoid provider-specific branching?
- Can tests inject a mock provider cleanly?
- Are error codes and payloads consistent across routes?
