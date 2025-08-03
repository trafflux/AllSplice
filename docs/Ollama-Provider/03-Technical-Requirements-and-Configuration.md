# Feature 03 — Technical Requirements and Configuration

Status: ✅ Complete

Purpose:
Detail environment assumptions, configuration, and connectivity for the Ollama provider, ensuring reliable operation within the Core OpenAI Endpoint Layer and alignment with organization standards.

Outcomes:
- Explicit env var contract and defaults.
- Connectivity and timeout behavior clearly specified.
- Non-streaming enforcement documented.
- Correlation propagation and observability fields defined.

Core Integration Context:
- Core handles transport/auth/validation and injects provider implementation (Core Feature 05).
- Provider uses Core config values (pydantic-settings) such as `REQUEST_TIMEOUT_S`.
- Correlation ID (request_id) is propagated from middleware; provider passes it to the client and logging.

Environment and Configuration (pydantic-settings):
- OLLAMA_HOST (e.g., `http://localhost:11434`) — required for local development; configurable per environment. Used as the base URL for all Ollama REST calls.
- REQUEST_TIMEOUT_S (default: 30) — applied to all outbound HTTP calls to Ollama via httpx.AsyncClient timeout.
- ENABLE_ENRICHMENT (default: False) — feature toggle for future enrichment; no behavior change in v1.0.
- LOG_LEVEL (default: INFO) — logging verbosity; no secrets in logs.
- ENABLE_SECURITY_HEADERS (default: true) — handled by core middleware (not provider).
- SERVICE_HOST/PORT — core service bind; provider does not bind sockets.

Connectivity:
- The Ollama REST API must be reachable at `OLLAMA_HOST`.
- Health of Ollama is out of scope for provider; failures are raised and normalized to `ProviderError` by the provider layer, then to HTTP 502 by the core exception handler.
- DNS/Network issues are not retried by default; fail fast with timeout from `REQUEST_TIMEOUT_S`.
- Localhost hermetic fallback: client provides deterministic fallback stubs only when `OLLAMA_HOST` is localhost and the transport layer fails; explicit HTTP 5xx and simulated httpx.ReadTimeout are propagated for normalization.

HTTP Client Configuration (implemented in src/ai_gateway/providers/ollama_client.py):
- httpx.AsyncClient with:
  - base URL = `OLLAMA_HOST`
  - timeout = `REQUEST_TIMEOUT_S`
  - headers: `Content-Type: application/json`
  - `X-Request-ID` header forwarded when available for tracing
- Methods:
  - GET /api/tags
  - POST /api/embeddings
  - POST /api/chat

Non-Streaming Enforcement (v1.0):
- Chat Completions only supports non-streaming in v1.0.
- If `stream=true` is provided, the provider raises `ProviderError`. Core normalizes to HTTP 502. No best-effort streaming emulation is attempted.

Error Normalization Path:
- Convert HTTP/network/timeouts into `ProviderError` with minimal public details (no upstream stack traces).
- HTTP status errors from Ollama are surfaced to the provider for normalization; transport exceptions trigger localhost fallback only in development scenarios as described above.

Logging and Redaction:
- Structured fields:
  - request_id, provider="ollama", method, path, status_code, duration_ms
- Redaction policy:
  - Do not log prompts, messages, embeddings, or secrets; log sizes/lengths only if necessary.
  - Known secret-like values (e.g., API keys) must never be included in logs or error messages.

Dependency Boundaries:
- Provider must not import core FastAPI/router modules.
- Accept typed OpenAI models from core schemas; return typed OpenAI responses.
- Clients are encapsulated in dedicated wrappers to keep third-party concerns isolated.

Examples:
- Minimal configuration via environment:
  - OLLAMA_HOST=http://localhost:11434
  - REQUEST_TIMEOUT_S=30
  - ENABLE_ENRICHMENT=false
- Correlation propagation:
  - Incoming request header `X-Request-ID` is captured by middleware and forwarded by the client; appears in structured logs.

Acceptance Criteria (met):
- Config and env vars documented; provider uses only config, no hard-coded URLs.
- HTTP client has explicit timeout and content-type defaults.
- Non-streaming stance documented and consistent with core endpoints.
- Logging fields standardized; no sensitive data recorded.

Test & Coverage Targets:
- Unit tests mocking HTTP client for timeout and error normalization.
- Tests verifying base URL and timeout taken from config.
- Logs verified to contain request_id and exclude secrets.

Review Checklist:
- Can the provider run against different OLLAMA_HOST without code changes? Yes.
- Are timeouts and non-streaming behavior consistent with core? Yes.
- Are logs structured and privacy-preserving? Yes.
