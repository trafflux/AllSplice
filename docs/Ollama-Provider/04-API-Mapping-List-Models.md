# Feature 04 — API Mapping: List Models (GET /{provider}/v1/models → GET /api/tags)

Status: ✅ Complete

Purpose:
Define the Ollama provider’s mapping for the core List Models method. Translate the core call `list_models()` into Ollama’s `GET /api/tags` and transform the response into the OpenAI ListModels schema.

Core Integration Reference:
- Core route: `GET /{provider}/v1/models` (Feature 07 of core).
- Provider interface method: `async def list_models(...) -> OpenAIListModelsResponse` (Core Feature 04).
- Errors normalized by core to HTTP 502 via `ProviderError`.
- Bearer auth enforced at transport layer by core; provider does not handle auth.
- Correlation ID available as `request_id`.

Ollama API:
- Endpoint: `GET {OLLAMA_HOST}/api/tags`
- Response (representative):
  {
    "models": [
      { "name": "llama3:latest", "modified_at": "2024-01-02T10:20:30Z" },
      { "name": "mistral:7b", "modified_at": "2023-12-15T08:00:00Z" }
    ]
  }

OpenAI Transformation Rules (per PRD):
- data.[].id ← models.[].name
- data.[].created ← Convert models.[].modified_at (ISO 8601) to Unix epoch seconds; fallback to current epoch on parse failure
- data.[].object ← "model"
- data.[].owned_by ← "ollama"
- top-level `object` ← "list"

Examples

Request:
GET /ollama/v1/models
Headers:
  Authorization: Bearer <API_KEY>
  X-Request-ID: 123e4567

Upstream (Ollama) response:
{
  "models": [
    { "name": "llama3:latest", "modified_at": "2024-01-02T10:20:30Z" }
  ]
}

Mapped OpenAI response:
{
  "object": "list",
  "data": [
    {
      "id": "llama3:latest",
      "object": "model",
      "created": 1704190830,
      "owned_by": "ollama"
    }
  ]
}

Edge Cases and Fallbacks:
- Empty or missing models array → return `{ "object": "list", "data": [] }` and log a warning.
- Invalid or missing modified_at → created set to current epoch; log a warning.
- Non-dict or malformed upstream JSON → provider normalizes to `ProviderError`.

Observability:
- Log fields: request_id, provider="ollama", method=GET, path=/api/tags, status_code, duration_ms.
- No model payload secrets are logged.

Acceptance Criteria:
- `list_models()` returns an OpenAI ListModels-compatible response as specified.
- Errors are normalized to `ProviderError` and surfaced as HTTP 502 by core.
- Empty/missing models handled deterministically.

Test & Coverage Targets:
- Unit tests (pytest-httpx):
  - Success mapping with one or more models.
  - Empty models array → empty OpenAI list.
  - Timestamp parse success and failure paths (fallback to now).
  - Timeout (httpx.ReadTimeout) and HTTP 5xx error normalization.
- Integration test via core route asserting schema shape and `WWW-Authenticate`/401/422/502 codes.

Review Checklist:
- Mandatory fields present and typed correctly.
- Created timestamp conversion robust to parse failures.
- No leakage of provider internals in errors.
