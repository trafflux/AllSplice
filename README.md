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
