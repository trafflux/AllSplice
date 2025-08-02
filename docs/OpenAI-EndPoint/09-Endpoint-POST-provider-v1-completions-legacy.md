# Feature 09 — Endpoint: POST /{provider}/v1/completions (Legacy)

Status: ⚠️ Incomplete

Purpose:
Define transport, validation, provider dispatch, and response shaping for the legacy OpenAI-compatible Text Completions endpoint. Maintain backward compatibility while prioritizing Chat Completions for new development.

Outcomes:
- Deterministic route for generating text completions across providers.
- Provider-agnostic dispatch to `create_completion()`.
- OpenAI Completion response compliance, including optional parameters.

Scope:
- Transport only: Parse `{provider}` from path, validate body against OpenAI Completion request schema (including optional params), resolve provider, call `create_completion()`, return OpenAI schema response.
- No provider-specific logic in the endpoint.
- Errors normalized via global handlers.
- Non-streaming behavior for v1 unless explicitly stated otherwise.

OpenAI Behavior Requirements:
- Path: `POST /{provider}/v1/completions`
- Request body conforms to OpenAI Completion request schema (e.g., `model`, `prompt`, and optional: `suffix`, `max_tokens`, `temperature`, `top_p`, `n`, `logprobs`, `echo`, `stop`, `presence_penalty`, `frequency_penalty`, `best_of`, `logit_bias`, `user`, `stream`).
- 200 OK with payload strictly conforming to OpenAI Completion response schema.
- Standard error codes:
  - 401 Unauthorized (missing/invalid token)
  - 404 Not Found (unknown provider)
  - 422 Unprocessable Entity (validation)
  - 502 Bad Gateway (provider failure via normalization)

Tasks:
1. Route Declaration
   - Document FastAPI route signature: `POST /{provider}/v1/completions`.
   - Require bearer auth.
   - Status: ⚠️

2. Request Validation
   - Validate body against OpenAI Completion request schema with all optional parameters recognized.
   - Forbid extra fields by default.
   - Status: ⚠️

3. Provider Resolution
   - Resolve `{provider}` via DI/registry.
   - Unknown provider → 404 standardized error payload.
   - Status: ⚠️

4. Invoke Provider
   - Call `await provider.create_completion(req)`.
   - Provide `request_id` and timeout context where applicable.
   - Streaming:
     - v1 default non-streaming; if `stream=true` is provided, return 404/405 or 400 per project decision; document behavior explicitly.
   - Status: ⚠️

5. Response Mapping
   - Ensure response matches OpenAI Completion response schema:
     - `id`, `object`, `created`, `model`, `choices`, `usage`
     - `choices[*].text`, `finish_reason`, `index`
     - When provider usage missing, set conservative defaults or zeros.
   - Status: ⚠️

6. Error Handling
   - Provider/network/timeout errors → `ProviderError` → 502 via handler.
   - Validation failures → 422 via global handler.
   - Auth failures → 401 with `WWW-Authenticate: Bearer`.
   - Status: ⚠️

7. Observability
   - Log `request_id`, `provider`, route, status_code, duration_ms.
   - Avoid logging prompts or generated text; log total character counts if needed.
   - Status: ⚠️

Dependencies:
- Feature 05 — Routing and Namespace Resolution.
- Feature 04 — Provider Interface Definition (create_completion()).
- Feature 06 — Authentication and Headers Handling.
- Global exception handlers and logging middleware.

Acceptance Criteria:
- Documented route and behavior satisfy OpenAI Completion API (legacy).
- Unknown provider returns standardized 404 error.
- Successful responses strictly match OpenAI response schema; errors normalized.
- Streaming behavior explicitly documented as out-of-scope for v1 unless otherwise enabled.

Test & Coverage Targets:
- Integration tests:
  - Success with mock provider returns correct OpenAI response shape.
  - Unknown provider → 404 standardized error.
  - Unauthorized → 401 with `WWW-Authenticate: Bearer`.
  - Validation errors (bad body) → 422 standardized payload.
  - If `stream=true` supplied, behavior matches documented decision.
- Logs include required fields; sensitive content not logged.

Review Checklist:
- No provider-specific branching in transport layer.
- OpenAI schema alignment verified for all required fields.
- Legacy constraints and streaming stance clearly documented.
