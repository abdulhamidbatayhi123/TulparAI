"""SQLite connection helpers + schema bootstrap.

Standalone CLI form: `python -m backend.db.connection` creates the DB file and
applies schema.sql idempotently.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from backend.config import settings

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Open (or create) the SQLite file and return a connection.

    `check_same_thread=False` because uvicorn workers may hand requests to
    different threads. SQLite is safe for the short-lived `with` blocks in repos.
    """
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.sqlite_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # cheap concurrency win
    return conn


def init_db() -> None:
    """Apply schema.sql idempotently (every statement uses IF NOT EXISTS)."""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
    print(f"DB initialised at {settings.sqlite_path}")


if __name__ == "__main__":
    init_db()
