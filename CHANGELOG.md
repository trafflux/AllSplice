# Changelog

All notable changes to this project will be documented in this file.

## [1.0.1] - 2025-08-03
### Added
- OpenAI compatibility updated (Phases 1–6+Streaming): permissive schemas, expanded fields, headers parity, embeddings dimensions, and Chat Completions streaming.
- SSE streaming for Ollama provider when `stream=true`; other providers return 501.
- Strict typing and linting per repo standards (ruff + mypy).
- Test suite green; coverage ~89% across src.

### Changed
- Improved response models to be more permissive to extra fields.

## [1.0.0] - 2025-08-01
### Added
- Initial release with basic OpenAI compatibility, Ollama provider, and Cerebras integration.
- Provider architecture and base interface.
- Authentication, routing, and health endpoint.
- Test suite and coverage enforcement.
