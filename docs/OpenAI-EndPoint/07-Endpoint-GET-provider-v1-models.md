# Feature 07 — Endpoint: GET /{provider}/v1/models

Status: ⚠️ Incomplete

Purpose:
Specify transport, validation, provider dispatch, and response shaping for the OpenAI-compatible List Models endpoint.

Outcomes:
- Deterministic route for listing models across providers.
- Provider-agnostic dispatch to `list_models()`.
- OpenAI ListModels response compliance.

Scope:
- Transport only: Parse `provider` from path, resolve provider, call `list_models()`, return OpenAI schema.
- No provider-specific logic embedded in the endpoint.
- Errors normalized via global handlers.

OpenAI Behavior Requirements:
- Path: `GET /{provider}/v1/models`
- 200 OK with payload strictly conforming to OpenAI ListModels schema.
- Standard error codes:
  - 401 Unauthorized (missing/invalid token)
  - 404 Not Found (unknown provider)
  - 422 Unprocessable Entity (validation)
  - 502 Bad Gateway (provider failure via normalization)

Tasks:
1. Route Declaration
   - Document FastAPI route signature: `GET /{provider}/v1/models`.
   - Ensure bearer auth is required and enforced.
   - Status: ⚠️

2. Provider Resolution
   - Resolve `{provider}` to an implementation via DI/registry.
   - Unknown provider → 404 standardized error payload.
   - Status: ⚠️

3. Invoke Provider
   - Call `await provider.list_models()`.
   - Provide `request_id` and timeout context if applicable.
   - Status: ⚠️

4. Response Mapping
   - Validate/ensure response matches OpenAI ListModels schema:
     - `object: "list"`
     - `data: [ { id, object: "model", created, owned_by, ... } ]`
   - Status: ⚠️

5. Error Handling
   - Provider/network/timeout errors → `ProviderError` → 502 via handler.
   - Validation failures → normalized 422.
   - Auth failures → 401 with `WWW-Authenticate: Bearer`.
   - Status: ⚠️

6. Observability
   - Log `request_id`, `provider`, route, status_code, duration_ms.
   - Status: ⚠️

Dependencies:
- Feature 05 — Routing and Namespace Resolution.
- Feature 04 — Provider Interface Definition (list_models()).
- Feature 06 — Authentication and Headers Handling.
- Global exception handlers and logging middleware.

Acceptance Criteria:
- Documented route and behavior satisfy OpenAI ListModels.
- Unknown provider returns 404 with standardized error.
- Responses are OpenAI-conformant on success; errors normalized.

Test & Coverage Targets:
- Integration tests:
  - Success path with mock provider → returns OpenAI list schema.
  - Unknown provider → 404 standardized error.
  - Unauthorized → 401 with `WWW-Authenticate: Bearer`.
- Ensure logs include required fields; no secret leakage.

Review Checklist:
- No provider-specific branching in the route.
- Response strictly matches OpenAI ListModels schema.
- Error semantics consistent with global standards.
