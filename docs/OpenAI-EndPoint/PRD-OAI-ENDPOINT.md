## Product Requirements Document: Universal AI Gateway - Core OpenAI Endpoint Layer
Version: 1.0
Status: Final
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
 "fastapi", "uvicorn", "uvicorn[standard]", "pydantic", "pydantic-settings", "cerebras-cloud-sdk", "ollama", "python-dotenv", "httpx", "anyio", "typing-extensions", "pytest", "pytest-asyncio", "pytest-cov", "ruff", "mypy", "pre-commit", "types-requests"
This project is run in a docker development environment inside Vscode and you are to only use ‘uv’ commands for execution and package management where applicable.
This is test driven development using strongly typed Python and to specific project standards. Follow the guidelines provided. Ensure compliance with mypy, ruff, and any other rules. Consult pyproject.toml for config specifications.  Code should follow best practices, be efficient, follow established project design patterns, and be highly reusable. Familiarize yourself with the codebase and try to use existing code where possible. Maintain DRY coding standards.
ALWAYS start by breaking down features into TASKS. Write a new file for every feature and store it in docs/OpenAI-EndPoint/{feature number}-{feature name}.md
You will then complete features 1 at a time and update the individual task statuses as:
✅ for complete, ⚠️ Incomplete, ❌ Incomplete and there is a blocking requirement for this stage of development, or ‼️which indicates a serious issue such as logical issue or impossibility.
Any blocking requirements need to be explained. When at the end of a feature you will review the task status for all items in that feature and any previous features to find any incomplete or incomplete with blocking that may be able to be resolved with the newest tasks completed.
Run pytest with coverage and ensure 85%+ coverage and passing of all tests that are not blocked by future requirements.
If you have any questions, ask the user.

1. Introduction
This document outlines the product requirements for creating the Core OpenAI Endpoint Layer for the Universal AI Gateway. The purpose of this project is to build a robust, provider-agnostic API interface that is fully compliant with the OpenAI REST API standards.
This core layer will act as a generic request handler and router. It will be designed with extreme reusability in mind, establishing a pluggable architecture where specific LLM providers (e.g., Ollama, Cerebras, etc.) can be integrated with minimal effort. The architecture will decouple the public-facing API endpoints from the backend implementation, allowing for rapid and scalable integration of new providers in the future.

2. Goals and Objectives
Primary Goal: To implement a set of high-fidelity, reusable endpoints that conform to the OpenAI REST API specification.
Architectural Goal: To create a modular, "provider-agnostic" system where new backend LLM providers can be added by creating a simple "provider module" and updating configuration, with no changes to this core API layer.
Decoupling: To ensure a clean separation of concerns between handling incoming API requests and the logic of communicating with a specific LLM provider.
Scalability: To build a foundation that can be easily extended to support additional OpenAI endpoints in the future (e.g., Image Generation, Audio).

3. Scope
In-Scope:
Implementation of a routing mechanism that directs incoming requests based on a URI segment (e.g., /provider_name/v1/...) to the appropriate backend provider module.
Creation of the following provider-agnostic OpenAI-compatible endpoints:
POST /<provider>/v1/chat/completions
POST /<provider>/v1/completions (for legacy support)
POST /<provider>/v1/embeddings
GET /<provider>/v1/models
Definition of a standard "Provider Interface" or base class that all backend provider modules must implement.
Handling of standard HTTP methods, headers, and response codes as per the OpenAI specification.

Out-of-Scope:
The implementation of any specific provider module (this will be handled in a separate project).
A graphical user interface (GUI) for configuration or management.
User authentication or authorization beyond the already in place bearer token authorization sent via headers. All endpoints must properly handle this system.
Rate-limiting can be considered for future versions

4. Functional Requirements
The Core Endpoint Layer must be capable of receiving, parsing, and routing requests for the following endpoints. It will then pass the request data to the designated provider module and ensure the final response conforms to the OpenAI standard.
4.1. Endpoint: GET /<provider>/v1/models
Description: Retrieves a list of models available from a specific provider.

Requirements:
The system MUST handle GET requests on the /<provider>/v1/models path.
It MUST identify the <provider> from the URL and invoke the list_models() method on the corresponding provider module.
It MUST return a JSON object that strictly conforms to the OpenAI ListModels schema.
It MUST return a 200 OK status code on success.
4.2. Endpoint: POST /<provider>/v1/embeddings
Description: Creates a vector embedding for a given input.
Requirements:
The system MUST handle POST requests on the /<provider>/v1/embeddings path.
It MUST parse and validate an incoming JSON body against the OpenAI CreateEmbeddingsRequest schema.
It MUST identify the <provider> and invoke the create_embeddings() method on the corresponding provider module.
It MUST return a JSON object that strictly conforms to the OpenAI CreateEmbeddingResponse schema.
It MUST return a 200 OK status code on success.
4.3. Endpoint: POST /<provider>/v1/completions
Description: Generates a text completion based on a prompt (Legacy).
Requirements:
The system MUST handle POST requests on the /<provider>/v1/completions path.
It MUST parse and validate an incoming JSON body against the OpenAI Completion request schema, including all optional parameters (max_tokens, temperature, stream, etc.).
It MUST identify the <provider> and invoke the create_completion() method on the corresponding provider module.
It MUST return a JSON object (or a stream of objects if requested) that strictly conforms to the OpenAI Completion schema.
It MUST return a 200 OK status code on success.
4.4. Endpoint: POST /<provider>/v1/chat/completions
Description: Generates a model response for a chat-based conversation.
Requirements:
The system MUST handle POST requests on the /<provider>/v1/chat/completions path.
It MUST parse and validate an incoming JSON body against the OpenAI ChatCompletion request schema, including the messages array and all optional parameters.
It MUST identify the <provider> and invoke the create_chat_completion() method on the corresponding provider module.
It MUST return a JSON object (or a stream of objects if requested) that strictly conforms to the OpenAI ChatCompletion schema.
It MUST return a 200 OK status code on success.
