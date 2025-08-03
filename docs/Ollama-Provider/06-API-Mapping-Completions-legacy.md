# Feature 06 — API Mapping: Completions (LEGACY) — Out of Scope in v1.0

Status: ✅ Complete (documented as excluded)

Purpose:
Document that legacy text completions endpoint `POST /{provider}/v1/completions` is explicitly excluded from v1.0 per the Core OpenAI Endpoint Layer OSI Final Summary. This file is retained to prevent confusion and to capture the mapping that would be required in a future version, but no implementation is required now.

Core Integration Reference:
- Core v1.0 scope excludes legacy completions. Provider Protocol only requires:
  - list_models()
  - create_embeddings(...)
  - chat_completions(...)
- Any references to `create_completion` are future-scope only.

Ollama API (for future reference only):
- Endpoint: `POST {OLLAMA_HOST}/api/generate`
- Non-streaming supported via `"stream": false`.
- Parameters like temperature/top_p/stop/seed/num_predict are nested in `"options"`.

OpenAI Transformation Rules:
- Not applicable in v1.0. See Chat Completions mapping in Feature 07 for supported generation.

Tasks:
- None for v1.0. Marking this feature excluded avoids accidental scope creep and aligns with the Core OSI Final Summary.

Observability:
- N/A for v1.0.

Streaming:
- N/A for v1.0; streaming is excluded globally.

Error Handling:
- N/A for v1.0.

Acceptance Criteria:
- This feature is explicitly marked out-of-scope for v1.0 and must not be implemented.
- Documentation must clearly direct users to Chat Completions for generation use cases.

Review Checklist:
- Does this page clearly state exclusion and rationale referencing OSI Final Summary?
- Are developers directed to Feature 07 for supported chat completions?
