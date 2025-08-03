## Product Requirements Document: AllSplice - Ollama Provider Integration & API Mapping
Version: 1.0
Status: Aligned with Core v1.0
Date: August 2, 2025

**Technology:**
Programming Language: Python 3.12.11
Framework: FastAPI
Testing Framework: Pytest
Type Checking: MyPy
Code Quality: Ruff
Development Environment: Docker, Visual Studio Code
OpenAI Api library

Other Dependencies:
"fastapi", "uvicorn", "uvicorn[standard]", "pydantic", "pydantic-settings", "httpx", "anyio", "typing-extensions", "pytest", "pytest-asyncio", "pytest-cov", "ruff", "mypy", "pre-commit"

You are to only use ‘uv’ commands for execution and package management where applicable.
This is test driven development using strongly typed Python and to specific project standards. Follow the guidelines provided. Ensure compliance with mypy, ruff, and any other rules. Consult pyproject.toml for config specifications.  Code should follow best practices, be efficient, follow established project design patterns, and be highly reusable. Familiarize yourself with the codebase and try to use existing code where possible. Maintain DRY coding standards.
ALWAYS start by breaking down features into TASKS. Write a new file for every feature and store it in docs/Ollama-Provider/{feature number}-{feature name}.md
You will then complete features 1 at a time and update the individual task statuses as:
✅ for complete, ⚠️ Incomplete, ❌ Incomplete and there is a blocking requirement for this stage of development, or ‼️which indicates a serious issue such as logical issue or impossibility.
Any blocking requirements need to be explained. When at the end of a feature you will review the task status for all items in that feature and any previous features to find any incomplete or incomplete with blocking that may be able to be resolved with the newest tasks completed.
Run pytest with coverage and ensure 85%+ coverage and passing of all tests that are not blocked by future requirements.
If you have any questions, ask the user.

1. Introduction
This document outlines the requirements for creating the Ollama Provider Module for the Universal AI Gateway. This project is dependent on the completion of the Core OpenAI Endpoint Layer (PRD v1.0).
The purpose of this module is to act as a translation layer that implements the standard Provider Interface defined in the core project. It will be responsible for mapping the standard OpenAI request objects received from the core layer into the specific format required by the Ollama REST API. It will also be responsible for transforming the responses from the Ollama API back into the standard OpenAI format before returning them to the core layer.

2. Goals and Objectives
Primary Goal: To create a fully functional provider module that allows the Universal AI Gateway to use a local Ollama instance as a backend LLM provider.
Seamless Integration: The module must flawlessly translate all supported parameters and data structures between the two API formats.
Compliance: The module must correctly implement all required methods from the gateway's "Provider Interface" base class.
Robustness: The module must gracefully handle potential errors or unexpected responses from the Ollama API.

3. Technical Requirements
The Ollama provider module will be configured to communicate with an Ollama instance, which is assumed to be running and accessible at the configured OLLAMA_HOST (default http://localhost:11434).
All outbound calls must use the explicit timeout REQUEST_TIMEOUT_S from config. The module will be invoked by the Core Endpoint Layer when an API request is made with the base URI segment /ollama/.

4. API Endpoint and Data Mapping Plan
This section details the specific transformations the module must perform for each endpoint.

In-scope for v1.0 (per Core OSI Final Summary):
- GET /<namespace>/models
- POST /<namespace>/embeddings
- POST /<namespace>/chat/completions

Out-of-scope for v1.0:
- POST /<namespace>/completions (legacy)
- Streaming responses (stream=true or SSE)

4.1. List Models (/v1/models) -> (/api/tags)
Core Layer Call: list_models()
Ollama API Call: GET /api/tags
Response Transformation: Map the Ollama models array to the OpenAI data array.
data.[].id <- models.[].name
data.[].created <- Convert models.[].modified_at from ISO 8601 to Unix epoch timestamp.
data.[].object <- Hardcode to "model".
data.[].owned_by <- Hardcode to "ollama".

4.2. Embeddings (/v1/embeddings) -> (/api/embeddings)
Core Layer Call: create_embeddings(request_body)
Ollama API Call: POST /api/embeddings
Request Transformation:
model <- model
prompt <- input
Response Transformation:
data.[].embedding <- embedding
data.[].index <- Hardcode to 0.
usage <- Create object with prompt_tokens and total_tokens set to 0.
object <- Hardcode to "list".
data.[].object <- Hardcode to "embedding".

4.3. Completions (LEGACY) — Excluded in v1.0
Not implemented per Core OSI Final Summary. Use Chat Completions instead.

4.4. Chat Completions (/v1/chat/completions) -> (/api/chat)
Core Layer Call: create_chat_completion(request_body)
Ollama API Call: POST /api/chat
Request Transformation:
model <- model
messages <- messages (Directly compatible structure).
stream <- must be non-streaming in v1.0; if provided as true by client, reject with ProviderError at provider or normalized at API layer.
format <- Translate OpenAI's response_format object to Ollama's format string (e.g., {"type": "json_object"} becomes "json").
All other optional parameters (temperature, stop, etc.) are nested within the options object, same as for /api/generate.
Response Transformation:
id <- Generate a unique ID (e.g., chatcmpl-...).
object <- "chat.completion".
created <- Convert created_at to Unix epoch timestamp (fallback to current epoch if absent).
choices[0].message <- message (Directly compatible object).
choices[0].finish_reason <- Map from done/done_reason; default "stop" when done==true.
usage fields are mapped from prompt_eval_count and eval_count; default zeros if missing.
