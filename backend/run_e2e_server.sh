#!/usr/bin/env bash
# Starts a FastAPI instance dedicated to E2E testing, backed by its own
# disposable SQLite file — completely separate from the developer's normal
# dev database (backend/language_delay.db, used by `uvicorn app.main:app`
# on the default port 8000). This script's server listens on port 8001.
#
# Every invocation deletes any previous E2E database file and re-runs
# migrations from scratch, so each E2E run starts from a known-empty,
# freshly-migrated state and never depends on (or pollutes) real
# development data or a previous test run's leftovers.
#
# Invoked automatically by frontend/playwright.config.ts's `webServer`
# array — not normally run by hand.
set -euo pipefail
cd "$(dirname "$0")"

VENV_BIN=".venv/Scripts"
[ -d "$VENV_BIN" ] || VENV_BIN=".venv/bin"

exec "$VENV_BIN/python" run_e2e_server.py
