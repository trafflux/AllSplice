# Feature 06 — Authentication and Headers Handling

Status: ⚠️ Incomplete

Purpose:
Specify how bearer token authentication and required HTTP headers are validated and propagated for all OpenAI-compatible endpoints within the Core OpenAI Endpoint Layer.

Outcomes:
- Uniform bearer token verification across all routes.
- Standardized security and response headers behavior.
- Clear failure semantics (401 with `WWW-Authenticate: Bearer`) and logging with correlation IDs.

Scope:
- Applies to all endpoints in this PRD:
  - GET `/{provider}/v1/models`
  - POST `/{provider}/v1/embeddings`
  - POST `/{provider}/v1/completions`
  - POST `/{provider}/v1/chat/completions`
- Uses existing middleware as specified by project standards.
- No new auth mechanisms are added in v1.

Tasks:
1. Bearer Token Validation
   - Enforce `Authorization: Bearer <API_KEY>` on all routes.
   - Validate against `ALLOWED_API_KEYS` (CSV) sourced from environment.
   - Trim whitespace, case-sensitive match as per standards.
   - Status: ⚠️

2. Failure Semantics
   - On auth failure return HTTP 401 and header `WWW-Authenticate: Bearer`.
   - Return standardized error payload per global handlers:
     {
       "error": {
         "type": "string",
         "message": "string",
         "details": { "optional": "object" }
       }
     }
   - Ensure no leakage of secrets to logs or responses.
   - Status: ⚠️

3. Security Headers
   - Apply default security headers when `ENABLE_SECURITY_HEADERS=true`:
     - `X-Content-Type-Options: nosniff`
     - `X-Frame-Options: DENY`
     - `Referrer-Policy: no-referrer`
     - `Permissions-Policy: ()` or minimal safe defaults
   - Status: ⚠️

4. Correlation and Request IDs
   - Read `X-Request-ID` if provided; otherwise generate new ID.
   - Propagate `request_id` via contextvars and include in logs.
   - Pass `request_id` to providers where possible.
   - Status: ⚠️

5. CORS (If Enabled)
   - Default disabled or restricted; document configuration switch.
   - Clearly state defaults for v1 and how to tighten/relax if needed.
   - Status: ⚠️

6. Observability and Redaction
   - Ensure structured logs include: `request_id`, `method`, `path`, `provider`, `status_code`, `duration_ms`.
   - Redact/avoid logging API keys and secrets.
   - Status: ⚠️

Dependencies:
- Project middleware: auth, correlation ID, security headers.
- Feature 05 — Routing and Namespace Resolution.
- Global exception handlers for standardized error payloads.

Acceptance Criteria:
- All OpenAI-compatible routes require bearer token auth with proper failure response.
- Security headers are applied per configuration.
- Request ID logged and propagated; secrets not logged.
- Documentation enumerates headers behavior for success and failure.

Test & Coverage Targets:
- API tests for:
  - Missing/invalid token → 401 with proper headers/payload.
  - Valid token → success path reaches handler.
  - Security headers present when enabled.
- Logs contain `request_id` and exclude token values.

Review Checklist:
- Is unauthorized behavior consistent and standardized?
- Are security headers correctly described and configurable?
- Does guidance prevent secret leakage in logs?
