#!/usr/bin/env bash
set -euo pipefail
export SERVICE_HOST="${SERVICE_HOST:-0.0.0.0}"
export SERVICE_PORT="${SERVICE_PORT:-8000}"
uvicorn ai_gateway.api.app:get_app --reload --host "$SERVICE_HOST" --port "$SERVICE_PORT"
