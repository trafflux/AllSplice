# Feature 04 — API Mapping: List Models (GET /{provider}/v1/models → GET /api/tags)

Status: ⚠️ Incomplete

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
      { "name": "llama3:latest", "modified_at": "2024-01-02T10:20:30Z", ... },
      ...
    ]
  }

OpenAI Transformation Rules (per PRD):
- data.[].id ← models.[].name
- data.[].created ← Convert models.[].modified_at (ISO 8601) to Unix epoch seconds
- data.[].object ← "model"
- data.[].owned_by ← "ollama"
- top-level `object` ← "list"

Tasks:
1. HTTP Call and Timeout
   - Perform GET `/api/tags` with base URL from `OLLAMA_HOST` and timeout from `REQUEST_TIMEOUT_S`.
   - Include `X-Request-ID` header if supported.
   - Status: ⚠️

2. Response Parsing
   - Validate presence of `models` array; handle empty arrays gracefully.
   - Status: ⚠️

3. Field Mapping
   - For each `models[i]`, map:
     - `id = name`
     - `created = epoch(modified_at)`; if missing/unparseable, use 0 and log warning (do not fail provider).
     - `object = "model"`
     - `owned_by = "ollama"`
   - Top-level `object = "list"`, `data = [...]`.
   - Status: ⚠️

4. Error Handling
   - Network/HTTP/timeout → raise normalized `ProviderError` with minimal message (no internals).
   - Malformed body (no models) → return empty list with `object="list"` and log warning.
   - Status: ⚠️

5. Observability
   - Log `request_id`, method=GET, path=/api/tags, status_code, duration_ms.
   - Status: ⚠️

Acceptance Criteria:
- `list_models()` returns an OpenAI ListModels-compatible response with fields populated as specified.
- On errors, core can convert exceptions to HTTP 502 via `ProviderError`.
- Empty/missing models handled deterministically (empty `data` with `object="list"`).

Test & Coverage Targets:
- Unit tests (mock HTTP):
  - Success mapping with 1+ models.
  - Empty models array → empty OpenAI list.
  - ISO 8601 parsing into epoch (valid and invalid cases).
  - Timeout and HTTP error normalization.
- Integration test via core route using this provider mock to assert schema shape.

Review Checklist:
- Are mandatory fields present and typed correctly?
- Is created timestamp correctly converted and robust to parse failures?
- Do errors avoid leaking provider internals?
