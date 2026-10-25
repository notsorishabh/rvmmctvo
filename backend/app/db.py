"""Read-only SQLite access. The deployed app never writes."""

import sqlite3
from pathlib import Path

from backend.app.config import DB_PATH


def connect_readonly(path: Path | None = None) -> sqlite3.Connection:
    """Open the prebuilt database without creating journals or lock files."""
    resolved = (path or DB_PATH).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"SQLite database not found: {resolved}")
    uri = f"file:{resolved.as_posix()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def fetch_all(connection: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
