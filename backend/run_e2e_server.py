"""Start the isolated E2E backend in one Playwright-owned process.

Keeping migration setup and Uvicorn in this Python process is important on
Windows: launching the server through Git Bash can detach the real Python
process, leaving Playwright unable to stop it after a run.
"""
from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from alembic.config import Config

from alembic import command

BACKEND_DIR = Path(__file__).resolve().parent
E2E_DB_FILE = BACKEND_DIR / "language_delay_e2e.db"


def main() -> None:
    os.chdir(BACKEND_DIR)
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./language_delay_e2e.db"

    E2E_DB_FILE.unlink(missing_ok=True)
    command.upgrade(Config(str(BACKEND_DIR / "alembic.ini")), "head")
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001)


if __name__ == "__main__":
    main()
