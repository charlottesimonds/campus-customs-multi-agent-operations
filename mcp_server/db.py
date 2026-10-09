"""Shared database helpers for the Campus Customs MCP server.

Every tool talks to the working copy, data/campus_customs_new.db. The original
data/campus_customs.db is never opened by the server.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"
ORIGINAL_DB_PATH = PROJECT_ROOT / "data" / "campus_customs.db"  # only ever read by reset_db.py


def _connect(mode: str) -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Working database not found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH.as_uri() + f"?mode={mode}", uri=True, isolation_level=None)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def read_connection():
    """Read-only connection; lookup tools cannot modify the database."""
    conn = _connect("ro")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def write_transaction():
    """Read-write connection inside one IMMEDIATE transaction.

    The write lock is taken up front, so a balance check and the update that
    depends on it cannot interleave with another writer. Commits on success,
    rolls back on any error.
    """
    conn = _connect("rw")
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def rows_to_dicts(rows) -> list[dict]:
    return [dict(row) for row in rows]


def get_shop_date(conn: sqlite3.Connection) -> date:
    """The shop's current date, taken from desk.date_today."""
    rows = conn.execute("SELECT date_today FROM desk").fetchall()
    if len(rows) != 1:
        raise RuntimeError(f"Expected exactly one row in desk, found {len(rows)}")
    return date.fromisoformat(rows[0]["date_today"])
