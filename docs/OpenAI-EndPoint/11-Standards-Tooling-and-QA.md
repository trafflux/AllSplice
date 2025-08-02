# Feature 11 — Standards, Tooling, and QA

Status: ⚠️ Incomplete

Purpose:
Codify engineering standards, tooling, and QA processes required by the PRD and project-wide standards to ensure the Core OpenAI Endpoint Layer is maintainable, mypy-clean, ruff-clean, and test-driven with adequate coverage.

Outcomes:
- Clear, enforceable standards for typing, linting/formatting, and tests.
- TDD workflow checklists mapped to features/endpoints.
- CI-ready expectations for coverage and static checks.

Scope:
- Python 3.12.11, FastAPI, Pytest, MyPy, Ruff, Docker, VS Code, uv (package manager).
- Strict typing and linting for all public functions/classes/modules.
- Non-functional QA requirements (coverage, static analysis) required before feature completion.

Tasks:
1. Typing Standards
   - Enforce strict type hints across public APIs, methods, and module variables.
   - Ensure project is mypy-clean under strict settings defined in pyproject.toml.
   - Document patterns: `list[T]`/`dict[K,V]`, `X | None`, Protocols for interfaces.
   - Status: ⚠️

2. Linting & Formatting
   - Use Ruff for both linting and formatting (single tool).
   - Adopt rule sets per project standards (E, F, W, N, I, C90, UP, B, A, C4, T20, SIM) and complexity limit 10.
   - Line length 100; import organization with isort settings (known-first-party = ["ai_gateway"], combine-as-imports = true).
   - Status: ⚠️

3. Pre-commit Hooks
   - Define mandatory hooks: ruff check, ruff format, mypy, whitespace, EOF newline.
   - Document local setup commands using uv where applicable.
   - Status: ⚠️

4. Test Strategy (TDD)
   - Write tests first for endpoints and provider mappings using pytest and pytest-asyncio.
   - Categories: unit tests (schemas, utils), integration tests (app factory, routers, DI), error-path tests (auth, validation, provider failures).
   - Mock external SDKs/services; no real calls in CI.
   - Status: ⚠️

5. Coverage Targets
   - Minimum ≥ 85% coverage for business logic.
   - Enforce via pytest-cov settings and CI gate.
   - Identify files excluded only when justified (e.g., __main__, generated code) — keep minimal.
   - Status: ⚠️

6. Docker & uv Usage
   - Document use of uv for dependency management and execution; `system = true` in containers.
   - Provide common commands for running tests and lint/type checks in Dockerized dev environment.
   - Status: ⚠️

7. CI Expectations
   - Pipeline stages: lint, type-check, test (with coverage).
   - Failure gates on mypy/ruff errors or insufficient coverage.
   - Status: ⚠️

8. Documentation Quality
   - Require docstrings for public classes/functions in Google or NumPy style.
   - Ensure no secrets in logs; redact known secret keys.
   - Status: ⚠️

Dependencies:
- Project-wide pyproject.toml configuration.
- Features 07–10 for endpoint-level tests and coverage.
- Feature 04 for provider interface and mapping tests.

Acceptance Criteria:
- Documented standards and commands clearly describe how to achieve mypy/ruff clean state.
- TDD guidance present for each endpoint/provider mapping with example checklists.
- Coverage requirement (≥ 85%) documented and enforced in instructions.

Test & Coverage Targets:
- Indirect: achieved through tests in endpoint/provider features.
- CI must report coverage and fail below threshold.

Review Checklist:
- Are standards comprehensive and aligned to project policies?
- Are commands and workflows feasible in the Docker + uv environment?
- Do the QA gates (mypy, ruff, coverage) block merges when failing?
