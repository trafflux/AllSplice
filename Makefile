# Makefile for AllSplice project

.PHONY: install precommit test lint format

install:
	uv pip install . --system

precommit: install
	pre-commit clean && pre-commit install --install-hooks

lint:
	ruff check src tests

test:
	PYTHONPATH=src pytest

.PHONY: lint format type test test-cov run hooks

lint:
	ruff .

type:
	mypy src

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=term-missing

run:
	uvicorn ai_gateway.api.app:get_app --reload --host 0.0.0.0 --port 8000

hooks:
	pre-commit install
	pre-commit run --all-files
