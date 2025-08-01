#!/usr/bin/env bash
set -euo pipefail

# Create directories
mkdir -p src/ai_gateway/{api,providers,schemas,config,exceptions,logging,middleware,utils}
mkdir -p tests/{api,providers,schemas,config,exceptions,logging,middleware,utils}
mkdir -p scripts docs .github/workflows

# Baseline files
touch src/ai_gateway/__init__.py
touch tests/__init__.py

# README.md
cat > README.md << 'EOF'
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
EOF

# .env.example
cat > .env.example << 'EOF'
# Universal AI Gateway — Environment Example (do not commit real secrets)

SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
ALLOWED_API_KEYS= # CSV; required in non-dev
CEREBRAS_API_KEY=
CEREBRAS_BASE_URL=
OLLAMA_HOST=http://localhost:11434
REQUEST_TIMEOUT_S=30
ENABLE_SECURITY_HEADERS=true
EOF

# CHANGELOG.md
cat > CHANGELOG.md << 'EOF'
# Changelog

## [Unreleased]
- Phase 0: Repo scaffolding, tooling, CI
EOF

# scripts/run_dev.sh
cat > scripts/run_dev.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
export SERVICE_HOST="${SERVICE_HOST:-0.0.0.0}"
export SERVICE_PORT="${SERVICE_PORT:-8000}"
uvicorn ai_gateway.api.app:get_app --reload --host "$SERVICE_HOST" --port "$SERVICE_PORT"
EOF
chmod +x scripts/run_dev.sh

# ruff.toml
cat > ruff.toml << 'EOF'
target-version = "py312"
line-length = 100
select = ["E", "F", "W", "N", "I", "C90"]
ignore = []
[lint.isort]
known-first-party = ["ai_gateway"]
combine-as-imports = true
force-single-line = false
EOF

# mypy.ini
cat > mypy.ini << 'EOF'
[mypy]
python_version = 3.12
strict = True
warn_unused_ignores = True
warn_redundant_casts = True
disallow_untyped_defs = True
no_implicit_optional = True
pretty = True

[mypy-tests.*]
disallow_untyped_defs = False
EOF

# pytest.ini
cat > pytest.ini << 'EOF'
[pytest]
addopts = -q -ra -W error::DeprecationWarning --cov=src --cov-report=term-missing
asyncio_mode = auto
testpaths = tests
EOF

# .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/psf/black
    rev: 24.4.2
    hooks:
      - id: black
        args: ["--line-length=100"]
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: ["--fix"]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
        additional_dependencies: []
        args: ["--config-file", "mypy.ini", "src"]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
EOF

# Makefile
cat > Makefile << 'EOF'
.PHONY: lint format type test test-cov run hooks

lint:
\truff .

format:
\tblack .

type:
\tmypy src

test:
\tpytest

test-cov:
\tpytest --cov=src --cov-report=term-missing

run:
\tuvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000

hooks:
\tpre-commit install
\tpre-commit run --all-files
EOF

# CI workflow
cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
  pull_request:

jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Lint (ruff)
        run: ruff .
      - name: Format check (black)
        run: black --check .
      - name: Type check (mypy)
        run: mypy src
      - name: Tests
        run: pytest --cov=src --cov-report=term-missing --cov-fail-under=85
EOF

# Update requirements.txt with runtime + dev deps (append if not present)
add_req() {
  pkg="$1"
  if ! grep -qiE "^${pkg}(==|\\[|$)" requirements.txt 2>/dev/null; then
    echo "${pkg}" >> requirements.txt
  fi
}

touch requirements.txt

# Runtime
add_req "fastapi"
add_req "uvicorn[standard]"
add_req "pydantic"
add_req "pydantic-settings"
add_req "httpx"
add_req "python-dotenv"
add_req "anyio"
add_req "typing-extensions"
add_req "cerebras-cloud-sdk"
add_req "ollama"

# Dev
add_req "pytest"
add_req "pytest-asyncio"
add_req "pytest-cov"
add_req "ruff"
add_req "mypy"
add_req "black"
add_req "pre-commit"
add_req "types-requests"

echo "Phase 0 scaffolding applied."
