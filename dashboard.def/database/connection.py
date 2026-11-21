"""Database connection handling.

Single point of access to SQLite: no other module in the project calls
sqlite3.connect() directly. This keeps the persistence choice in one place,
so swapping SQLite for another engine touches this file and nothing else.
"""
import sqlite3
from contextlib import contextmanager

from config import DB_PATH

from .schema import ALL_STATEMENTS


@contextmanager
def get_connection(read_only: bool = False):
    """Yield a SQLite connection and always close it, errors included.

    Args:
        read_only: open the database in read-only mode. Used by the dashboard
            so that an accidental write raises immediately instead of
            silently corrupting the data produced by the ETL.

    Yields:
        sqlite3.Connection with row_factory set to sqlite3.Row, so query
        results behave like dictionaries (row["close"]) as well as tuples.
    """
    if read_only:
        connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
    finally:
        connection.close()


def initialise_schema() -> None:
    """Create every table and index if missing.

    Idempotent: every statement uses IF NOT EXISTS, so running it on an
    existing database is a no-op and never destroys data.
    """
    with get_connection() as connection:
        for statement in ALL_STATEMENTS:
            connection.execute(statement)
        connection.commit()


def database_exists() -> bool:
    """True when the database file is present and holds at least one table.

    Used by the dashboard at start-up to tell the user to run the ETL
    instead of failing with a raw SQLite error.
    """
    if not DB_PATH.exists():
        return False
    try:
        with get_connection(read_only=True) as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS n FROM sqlite_master WHERE type = 'table'"
            ).fetchone()
        return bool(row and row["n"] > 0)
    except sqlite3.Error:
        return False