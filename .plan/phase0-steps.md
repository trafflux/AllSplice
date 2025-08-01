Implement Phase 0 — Repo Scaffolding and CI/CD

This file tracks the exact steps executed during Phase 0.

1) Create directories
- src/ai_gateway/{api,providers,schemas,config,exceptions,logging,middleware,utils}
- tests/{api,providers,schemas,config,exceptions,logging,middleware,utils}
- scripts, docs, .github/workflows

2) Baseline files
- src/ai_gateway/__init__.py
- tests/__init__.py
- README.md (skeleton)
- .env.example
- CHANGELOG.md
- scripts/run_dev.sh

3) Tooling config files
- ruff.toml
- mypy.ini
- pytest.ini
- .pre-commit-config.yaml
- Makefile

4) CI workflow
- .github/workflows/ci.yml

5) requirements.txt update
- Add runtime and dev dependencies.
