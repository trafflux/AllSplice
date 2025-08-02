# Universal AI Gateway

OpenAI-compatible API server to route chat completions to multiple providers (Custom, Cerebras, Ollama).

## Status
Phase 0 scaffolding and CI/CD setup.

## Docs
- PRD: PRD-1.0.md
- Tasks: TASKS-1.0.md
- Standards: PROJECT-STANDARDS.md

## Quickstart (after Phase 4)
- Run (dev): `uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000`

## Usage

The service exposes multiple provider-compatible endpoints following the OpenAI Chat Completions format.

### Default (Custom) — POST /v1/chat/completions

Example:
```bash
curl -s -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "custom-mock",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### Cerebras — POST /cerebras/v1/chat/completions

Example:
```bash
curl -s -X POST "http://localhost:8000/cerebras/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "cerebras-gpt",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```

### Ollama — POST /ollama/v1/chat/completions

Requires OLLAMA_HOST configured (e.g., http://localhost:11434). Example:
```bash
curl -s -X POST "http://localhost:8000/ollama/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1",
    "messages": [
      {"role": "user", "content": "Hello"}
    ]
  }'
```
