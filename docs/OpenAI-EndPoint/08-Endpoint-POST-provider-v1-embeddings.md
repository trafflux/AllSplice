# Feature 08 — Endpoint: POST /{provider}/v1/embeddings

Status: ⚠️ Incomplete

Purpose:
Define transport, validation, provider dispatch, and response shaping for the OpenAI-compatible Create Embeddings endpoint.

Outcomes:
- Deterministic route for creating embeddings across providers.
- Provider-agnostic dispatch to `create_embeddings()`.
- OpenAI CreateEmbeddingResponse compliance.

Scope:
- Transport only: Parse `{provider}` from path, validate body against OpenAI CreateEmbeddings request schema, resolve provider, call `create_embeddings()`, return OpenAI schema response.
- No provider-specific logic in the endpoint.
- Errors normalized via global handlers.

OpenAI Behavior Requirements:
- Path: `POST /{provider}/v1/embeddings`
- Request body conforms to OpenAI CreateEmbeddingsRequest (e.g., `model`, `input`, optional parameters).
- 200 OK with payload strictly conforming to OpenAI CreateEmbeddingResponse.
- Standard error codes:
  - 401 Unauthorized (missing/invalid token)
  - 404 Not Found (unknown provider)
  - 422 Unprocessable Entity (validation)
  - 502 Bad Gateway (provider failure via normalization)

Tasks:
1. Route Declaration
   - Document FastAPI route signature: `POST /{provider}/v1/embeddings`.
   - Require bearer auth.
   - Status: ⚠️

2. Request Validation
   - Validate body against OpenAI CreateEmbeddingsRequest schema, including array/string inputs and optional fields.
   - Reject extra fields (forbid by default).
   - Status: ⚠️

3. Provider Resolution
   - Resolve `{provider}` to implementation via DI/registry.
   - Unknown provider → 404 standardized error payload.
   - Status: ⚠️

4. Invoke Provider
   - Call `await provider.create_embeddings(req)`.
   - Provide `request_id` and timeout context where applicable.
   - Status: ⚠️

5. Response Mapping
   - Ensure response matches OpenAI CreateEmbeddingResponse:
     - `object: "list"`
     - `data: [ { object: "embedding", index, embedding: [float,...] } ]`
     - `model`, `usage` fields present per spec (if provider missing usage, set conservative defaults or zeros).
   - Status: ⚠️

6. Error Handling
   - Provider/network/timeout errors → `ProviderError` → 502 via handler.
   - Validation failures → 422 via global handler.
   - Auth failures → 401 with `WWW-Authenticate: Bearer`.
   - Status: ⚠️

7. Observability
   - Log `request_id`, `provider`, route, status_code, duration_ms.
   - Do not log embedding vectors or sensitive input content; log sizes/lengths only if needed.
   - Status: ⚠️

Dependencies:
- Feature 05 — Routing and Namespace Resolution.
- Feature 04 — Provider Interface Definition (create_embeddings()).
- Feature 06 — Authentication and Headers Handling.
- Global exception handlers and logging middleware.

Acceptance Criteria:
- Documented route and behavior satisfy OpenAI CreateEmbeddings API.
- Unknown provider returns standardized 404 error.
- Successful responses strictly match OpenAI response schema; errors normalized.

Test & Coverage Targets:
- Integration tests:
  - Success with mock provider returns correct OpenAI response shape.
  - Unknown provider → 404 standardized error.
  - Unauthorized → 401 with `WWW-Authenticate: Bearer`.
  - Validation errors (bad body) → 422 standardized payload.
- Logs include required fields; embeddings not logged.

Review Checklist:
- No provider-specific branching in route logic.
- Response strictly matches OpenAI embedding response schema.
- Sensitive information not logged.
