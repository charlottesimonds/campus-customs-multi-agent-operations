"""Reset the working database to the original.

Restores every table in data/campus_customs_new.db from data/campus_customs.db
inside one IMMEDIATE transaction:

- the original is attached read-only, so it can never be modified;
- if another connection is mid-write, the reset waits at most BUSY_TIMEOUT_S
  and then fails with DatabaseBusy instead of interrupting that transaction;
- readers never see a half-reset database (the swap commits all at once);
- afterwards the two databases are compared row by row.

Used by the MCP tool reset_working_database and runnable directly before a
full ticket-resolution run, from the Homework 5 folder:
    .venv/bin/python -m mcp_server.reset_db
"""

import sqlite3

from .db import DB_PATH, ORIGINAL_DB_PATH

BUSY_TIMEOUT_S = 5


class DatabaseBusy(RuntimeError):
    """Another connection holds a write lock; the reset was not started."""


def _schema(conn: sqlite3.Connection, schema: str) -> list[tuple]:
    return conn.execute(
        f"SELECT type, name, sql FROM {schema}.sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
    ).fetchall()


def _tables(conn: sqlite3.Connection, schema: str) -> list[str]:
    return [r[0] for r in conn.execute(f"SELECT name FROM {schema}.sqlite_master WHERE type = 'table' "
                                       "AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def _rows(conn: sqlite3.Connection, schema: str, table: str) -> list[tuple]:
    return conn.execute(f'SELECT * FROM {schema}."{table}" ORDER BY 1, 2').fetchall()


def reset_working_database() -> dict:
    """Restore the working copy from the original. Returns per-table row counts."""
    for path in (ORIGINAL_DB_PATH, DB_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Database not found at {path}")

    # Opened as a URI so the original can be attached with mode=ro.
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=rw", uri=True, timeout=BUSY_TIMEOUT_S, isolation_level=None)
    try:
        conn.execute("ATTACH DATABASE ? AS original", (ORIGINAL_DB_PATH.as_uri() + "?mode=ro",))
        if _schema(conn, "main") != _schema(conn, "original"):
            raise RuntimeError("Working database schema differs from the original; refusing to reset.")
        tables = _tables(conn, "original")

        try:
            conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            raise DatabaseBusy(f"Working database is busy ({exc}); no changes were made.") from exc
        try:
            conn.execute("PRAGMA defer_foreign_keys = ON")
            for table in tables:
                conn.execute(f'DELETE FROM main."{table}"')
                conn.execute(f'INSERT INTO main."{table}" SELECT * FROM original."{table}"')
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise

        mismatched = [t for t in tables if _rows(conn, "main", t) != _rows(conn, "original", t)]
        if mismatched:
            raise RuntimeError(f"Reset verification failed for tables: {mismatched}")
        counts = {t: conn.execute(f'SELECT COUNT(*) FROM main."{t}"').fetchone()[0] for t in tables}
    finally:
        conn.close()
    return {"restored_from": ORIGINAL_DB_PATH.name, "restored_to": DB_PATH.name, "verified": True,
            "row_counts": counts}


if __name__ == "__main__":
    result = reset_working_database()
    print(f"Reset {result['restored_to']} from {result['restored_from']}; verified identical. Rows: {result['row_counts']}")
