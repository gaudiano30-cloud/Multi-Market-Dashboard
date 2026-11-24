"""Centralised database connection and non-destructive schema upgrades."""
import sqlite3
from contextlib import contextmanager

from config import DB_PATH
from .schema import INDEXES, MARKETS_EXTRA_COLUMNS, TABLES


@contextmanager
def get_connection(read_only: bool = False):
    if read_only:
        # SQLite URI mode=ro prevents accidental dashboard writes.
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
    """Create missing tables; add geographical columns to older DBs safely."""
    with get_connection() as connection:
        for statement in TABLES:
            connection.execute(statement)
        existing = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(markets)")
        }
        for column, data_type in MARKETS_EXTRA_COLUMNS.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE markets ADD COLUMN {column} {data_type}")
        for statement in INDEXES:
            connection.execute(statement)
        connection.commit()


def database_exists() -> bool:
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
