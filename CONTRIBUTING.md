# Contributing to AllSplice

Thank you for your interest in contributing to AllSplice! We welcome issues, feature requests, and pull requests from the community.

## Getting Started

- **Python 3.12+** is required.
- Install dependencies using [uv](https://github.com/astral-sh/uv):
  ```bash
  uv pip install -e .
  ```
- Copy `.env.example` to `.env` and configure your environment variables.
- Run the development server:
  ```bash
  uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000
  ```

## Code Standards

- Follow the repo's strict typing and linting rules (see `pyproject.toml`).
- All code must be formatted and linted with Ruff, and type-checked with mypy.
- Tests are required for all new features and bugfixes (pytest + pytest-asyncio).
- Coverage must remain ≥ 85% for business logic.
- All tool configs are in `pyproject.toml` (no separate config files).

## Pre-commit Hooks

- Install pre-commit and run hooks before committing:
  ```bash
  pre-commit install
  pre-commit run --all-files
  ```
- Hooks check formatting, linting, typing, YAML, merge conflicts, large files, and debug statements.

## Making a Pull Request

- Fork the repo and create a feature branch.
- Ensure all tests pass locally:
  ```bash
  pytest --cov=src --cov-report=term-missing
  ```
- Open a pull request with a clear description of your changes.
- Link related issues if applicable.
- Update documentation and `.env.example` if you add or change environment variables.

## Provider Contributions

- Add new providers under `src/ai_gateway/providers/`.
- Implement the base protocol in `providers/base.py`.
- Add tests for both success and error paths.
- Ensure OpenAI request/response mapping is complete.

## Community Standards

- Do whatever you want, as long as it doesn't break the code.

## Questions?

Open an issue or join the discussion on GitHub!
