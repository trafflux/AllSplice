# Feature 05 — API Mapping: Embeddings (POST /{provider}/v1/embeddings → POST /api/embeddings)

Status: ✅ Complete

Purpose:
Define the Ollama provider mapping for embeddings. Translate the core call `create_embeddings(req)` into Ollama’s `POST /api/embeddings` and transform the response into the OpenAI CreateEmbeddingResponse schema.

Core Integration Reference:
- Core route: `POST /{provider}/v1/embeddings` (Core Feature 08).
- Provider interface method: `async def create_embeddings(req) -> OpenAICreateEmbeddingsResponse` (Core Feature 04).
- Core enforces auth/validation and normalizes exceptions.
- Correlation ID propagated as `request_id`.
- Non-streaming v1 default.

Ollama API:
- Endpoint: `POST {OLLAMA_HOST}/api/embeddings`
- Request (representative):
  {
    "model": "llama3",
    "prompt": "text to embed"
  }
- Response (representative):
  {
    "embedding": [0.1, 0.2, ...],
    "model": "llama3",
    "created_at": "2024-01-02T10:20:30Z"
  }

OpenAI Transformation Rules (per PRD):
- Request:
  - `model` ← req.model
  - `prompt` ← req.input (support string or list[str]; one POST per item)
- Response:
  - `object` ← "list"
  - `data[i].object` ← "embedding"
  - `data[i].embedding` ← response.embedding
  - `data[i].index` ← i
  - `model` ← response.model or req.model
  - `usage` ← { "prompt_tokens": 0, "total_tokens": 0 }
  - `created` ← epoch(response.created_at) if available; otherwise omit

Examples

Single input request (OpenAI):
POST /ollama/v1/embeddings
{
  "model": "llama3",
  "input": "The quick brown fox"
}

Upstream (Ollama) per-call request:
{ "model": "llama3", "prompt": "The quick brown fox" }

Upstream response:
{ "embedding": [0.1, 0.2], "model": "llama3", "created_at": "2024-01-02T10:20:30Z" }

Mapped OpenAI response:
{
  "object": "list",
  "data": [
    { "object": "embedding", "index": 0, "embedding": [0.1, 0.2] }
  ],
  "model": "llama3",
  "usage": { "prompt_tokens": 0, "total_tokens": 0 },
  "created": 1704190830
}

List input request (OpenAI):
POST /ollama/v1/embeddings
{
  "model": "llama3",
  "input": ["a", "b"]
}

Behavior (v1.0):
- Sequential per-item POSTs to /api/embeddings with prompt equal to each string.
- Aggregate results preserving input order; indices 0..n-1.

Mapped OpenAI response:
{
  "object": "list",
  "data": [
    { "object": "embedding", "index": 0, "embedding": [0.1, 0.2] },
    { "object": "embedding", "index": 1, "embedding": [0.3, 0.4] }
  ],
  "model": "llama3",
  "usage": { "prompt_tokens": 0, "total_tokens": 0 }
}

Edge Cases and Fallbacks:
- Upstream missing `embedding` or non-list shape:
  - Provider returns deterministic fallback vectors for CI hermeticity when the client indicates localhost transport fallback conditions.
  - Otherwise, provider raises `ProviderError`.
- Upstream missing `model` → set to req.model.
- For list input, any per-item upstream failure causes the entire request to fail in v1.0 (fail-fast policy), ensuring deterministic behavior.
- Numerical types preserved: vectors are lists of float.

Observability:
- Log fields: request_id, provider="ollama", method=POST, path=/api/embeddings, status_code, duration_ms.
- Do not log embeddings or raw prompts; log counts only (e.g., items=n, dims=len(vector)) if needed.

Acceptance Criteria:
- `create_embeddings()` returns a valid OpenAI embeddings response for string and list inputs.
- Usage zeros present; model mapped; created parsed to epoch when available.
- Errors normalized without leaking internals; deterministic behavior documented.

Test & Coverage Targets (pytest-httpx):
- Single input string → maps to one embedding item.
- List input → sequential calls; ordering and indices preserved.
- Missing `embedding` → ProviderError unless localhost deterministic fallback path applies.
- Timeout (httpx.ReadTimeout) and HTTP 5xx errors normalized.
- Integration test via core route ensuring OpenAI schema compliance.

Review Checklist:
- OpenAI input cardinality honored.
- Numerical types preserved (list[float]).
- Logs include request_id and exclude sensitive payloads.
