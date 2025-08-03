# AllSplice — Universal AI Gateway ![CI](https://github.com/trafflux/AllSplice/actions/workflows/ci.yml/badge.svg)
**version 1.0.1**
AllSplice is a universal, OpenAI-compatible gateway that lets you plug AI agents/clients into multiple model providers (local and commercial) with a consistent API. Think of it as a breakout board for AI — it exposes and normalizes the “pre-packaged, behind-the-scenes” data a client sends to a provider so you can inspect, augment, and reroute it without changing your app.

Core goals:
- OpenAI API compatibility for maximum interoperability with existing SDKs and tooling.
- Pluggable providers (Ollama, Cerebras, custom) with uniform request/response mapping.
- Policy, logging, and transformation points where developers can customize prompts, context, and responses.
- Works for local development (e.g., Ollama on localhost) and standard cloud providers.

Use cases:
- Swap model backends (local -> cloud) without changing your agent code.
- Enrich/inspect requests or responses (add system prompts, enforce policies, redact PII).
- Capture structured logs and request IDs for observability.

## Status

v1.0.1 implementation complete with authentication, routing, provider integration, and streaming (SSE) for Ollama.

Highlights:
- OpenAI compatibility updated (Phases 1–6+Streaming): permissive schemas, expanded fields, headers parity, embeddings dimensions, and Chat Completions streaming.
- SSE streaming for Ollama provider when `stream=true`; other providers return 501.
- Test suite green; coverage ~89% across src.
- Strict typing and linting per repo standards (ruff + mypy).

v1.0.0 was the initial release with basic OpenAI compatibility, Ollama provider, and Cerebras integration. This lacked streaming and some advanced OpenAI features but provided a solid foundation for future enhancements.

## Quickstart

### Prerequisites
- Python 3.12+
- uv package manager

### Setup
```bash
# Clone
git clone https://github.com/trafflux/AllSplice.git
cd AllSplice

# Install dependencies (requires Python 3.12+ and uv)
uv pip install -e .

# Copy environment template
cp .env.example .env

# Edit .env with your configuration (see below for details)

# Run in development mode
uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000
```

### Development Mode
For local development, set `DEVELOPMENT_MODE=true` in your `.env` file. This relaxes authentication requirements while still allowing you to test the API structure.

## Configuration

See `.env.example` for all available environment variables. Key settings include:
- `ALLOWED_API_KEYS`: Comma-separated list of valid API keys (required in production) ex: ['key1','key2','key3']
- `CEREBRAS_API_KEY`: API key for Cerebras provider
- `CEREBRAS_BASE_URL`: Optional custom Cerebras endpoint
- `OLLAMA_HOST`: Ollama server URL (default: http://localhost:11434)
- `REQUEST_TIMEOUT_S`: Request timeout in seconds (default: 30)
- `ENABLE_SECURITY_HEADERS`: Enable security headers (default: true)

## Docs

- PRD: docs/PRD-Initial-v1.0/PRD-Initial-Scope-v1.0.md
- OpenAI Endpoint Design: docs/OpenAI-EndPoint/
- OAI Standards Report: docs/OAI-Standards/Report.md
- OAI Change Log: docs/OAI-Standards/OAI-CHANGE-LOG.md
- Streaming Plan and Status: docs/OAI-Standards/Streaming.md
## Contributing

AllSplice is designed to make it simple to add or improve providers.

- Provider architecture: see src/ai_gateway/providers/
  - Base interface in providers/base.py; concrete providers implement chat_completions (and optionally stream_chat_completions).
  - Client wrappers encapsulate third-party SDKs/HTTP surface.
- Add a provider:
  - Create a new module under providers/, implement the base protocol, wire it in the app composition root and routes.
  - Ensure mapping to OpenAI request/response is complete and add tests for both happy-path and error-path.
- Standards:
  - Python 3.12+, ruff for linting/formatting, mypy strict typing.
  - Tests with pytest + pytest-asyncio, coverage target ≥ 85%.
  - All tool configs live in pyproject.toml.

Roadmap ideas:
- Additional providers (OpenAI, Google Gemini, Anthropic, Azure OpenAI).
- Pluggable request/response middlewares for redaction, policy enforcement, and prompt templating.
- Tracing and metrics exporters.

If you want to contribute, open an issue or PR. Please include tests, follow repo style, and update docs as needed.
- PRD: docs/PRD-Initial-v1.0/PRD-Initial-Scope-v1.0.md
- OpenAI Endpoint Design: docs/OpenAI-EndPoint/
- OAI Standards Report: docs/OAI-Standards/Report.md
- OAI Change Log: docs/OAI-Standards/OAI-CHANGE-LOG.md

## Local Development

- Run (dev): `uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000`
- Verify health: `curl -s http://localhost:8000/healthz`
- Logs and correlation IDs: responses include both `X-Request-ID` and `x-request-id`.

## API Endpoints

All endpoints follow the OpenAI Chat Completions API format and require authentication via Bearer token.

Compatibility highlights:
- Requests are permissive (extra fields ignored) to accommodate evolving OpenAI SDK parameters.
- Chat messages accept content as string or minimal parts (text, image_url). Roles include system, user, assistant, tool, developer, function.
- Frequently used OpenAI fields supported on /chat/completions requests:
  - user, logit_bias, logprobs, top_logprobs, tools, tool_choice, functions, function_call,
    response_format, stream, stream_options, seed, metadata, store, parallel_tool_calls.
- Streaming:
  - OpenAI-compatible SSE is implemented for Ollama when `stream=true`, with chunk objects and `[DONE]` sentinel.
  - Non-Ollama providers return 501 for streaming requests in v1.0.
- Response parity:
  - Choice supports optional logprobs when available; response models are permissive to extra fields.
- Headers:
  - Responses include both X-Request-ID and x-request-id for SDK compatibility.
  - 401 includes WWW-Authenticate: Bearer.

### Health Check — GET /healthz
```bash
curl -X GET "http://localhost:8000/healthz"
```

### Default (Custom) — POST /v1/chat/completions
Routes to Custom Processing Provider (mock responses for development).

Example:
```bash
curl -s -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### Cerebras — POST /cerebras/v1/chat/completions
Routes to Cerebras Cloud API (requires CEREBRAS_API_KEY).

Example:
```bash
curl -s -X POST "http://localhost:8000/cerebras/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8b",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in simple terms"}
    ]
  }'
```

### Ollama — POST /ollama/v1/chat/completions

Routes to local or remote Ollama instance (requires OLLAMA_HOST configured).

Non-streaming example:
```bash
curl -s -X POST "http://localhost:8000/ollama/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "granite3.3:2b",
    "messages": [
      {"role": "developer", "content": "You are a helpful assistant."},
      {"role": "user", "content": [
        {"type": "text", "text": "Write a Python function to calculate Fibonacci numbers"}
      ]}
    ],
    "response_format": {"type": "json_object"},
    "logprobs": true,
    "top_logprobs": 5,
    "user": "example-user"
  }'
```

Streaming example (SSE):
```bash
curl -N -X POST "http://localhost:8000/ollama/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3",
    "stream": true,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```
Response:
- Content-Type: text/event-stream
- Frames: `data: {json}\n\n` for each chunk, then `data: [DONE]\n\n`
- Headers include both `X-Request-ID` and `x-request-id`
- Each chunk is an OpenAI-style object: `{"object":"chat.completion.chunk","choices":[{"delta":{"content":"..."}}], ...}`

Notes:
- For JSON responses, set response_format to {"type":"json_object"}.
- If logprobs are supported upstream, Choice.logprobs may be present in the response.
- Streaming: For Ollama, SSE is supported when `stream=true`. The response uses `text/event-stream` with OpenAI-compatible chunk objects and terminates with a `[DONE]` sentinel. For other providers, a 501 Not Implemented JSON error is returned when `stream=true`.
- Request IDs: All responses include both `X-Request-ID` and `x-request-id`. Clients and logs can correlate using either header name.

## Authentication

All endpoints require an `Authorization: Bearer <API_KEY>` header. In development mode, authentication is relaxed but still recommended for testing.

Headers behavior:
- Request ID: Responses include both `X-Request-ID` and `x-request-id`.
- Unauthorized: 401 responses include `WWW-Authenticate: Bearer`.

### Development Mode

Set `DEVELOPMENT_MODE=true` in your environment to enable relaxed authentication. This allows testing without requiring valid API keys, but still validates the request structure.

### Production Mode

In production, configure `ALLOWED_API_KEYS` with a comma-separated list of valid API keys. The service will reject requests with unauthorized keys.

## Testing

Run the test suite:
```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=src --cov-report=term-missing
```

What to look for:
- Chat: Accepts extra OpenAI fields (tools/tool_choice/response_format/logprobs/etc.) without 422.
- Messages: Accepts content as string or minimal parts (text/image_url); supports developer/function roles.
- Headers: Response includes both X-Request-ID and x-request-id; 401 contains WWW-Authenticate: Bearer.
- Embeddings: Accepts dimensions and forwards to provider when supported; deterministic fallbacks respect the requested dimensions in dev/local mode.
- Streaming: SSE tests validate proper event framing and `[DONE]` sentinel for Ollama.
