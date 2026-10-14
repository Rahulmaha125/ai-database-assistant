"""SQLite database connection and query execution utilities."""

import os
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class DatabaseError(Exception):
    """Raised when database query execution fails."""
    pass


class ReadOnlyViolationError(DatabaseError):
    """Raised when a write query is attempted on a read-only connection."""
    pass


def get_connection(db_path: str | Path, read_only: bool = False, timeout: float = 10.0) -> sqlite3.Connection:
    """Create a SQLite database connection.

    Args:
        db_path: Path to the SQLite database file.
        read_only: If True, opens connection in read-only mode via URI and PRAGMA query_only.
        timeout: Query lock timeout in seconds.

    Returns:
        sqlite3.Connection object.
    """
    path = Path(db_path).resolve()
    if not path.exists() and read_only:
        raise FileNotFoundError(f"Database file not found: {path}")

    if read_only:
        # Use SQLite URI mode for strict read-only access
        posix_path = path.as_posix()
        uri = f"file:{posix_path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=timeout)
        try:
            conn.execute("PRAGMA query_only = ON;")
        except sqlite3.Error:
            pass
    else:
        conn = sqlite3.connect(str(path), timeout=timeout)

    conn.row_factory = sqlite3.Row
    return conn


def execute_query(
    db_path: str | Path,
    query: str,
    params: Optional[Tuple[Any, ...] | Dict[str, Any]] = None,
    read_only: bool = True,
    timeout: float = 10.0,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute a SQL query against SQLite database safely.

    Args:
        db_path: Path to SQLite database.
        query: SQL query string.
        params: Optional SQL parameters.
        read_only: Whether to execute in read-only mode.
        timeout: Execution timeout in seconds.
        max_rows: Maximum rows to return before truncating.

    Returns:
        Dict containing columns, rows, row_count, execution_time_ms, and truncated flag.
    """
    start_time = time.perf_counter()
    conn = None
    try:
        conn = get_connection(db_path, read_only=read_only, timeout=timeout)
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        
        if max_rows is not None and max_rows > 0:
            rows = cursor.fetchmany(max_rows + 1)
            truncated = len(rows) > max_rows
            if truncated:
                rows = rows[:max_rows]
        else:
            rows = cursor.fetchall()
            truncated = False

        # Convert rows to standard list of dicts/lists for easy consumption
        row_list = [list(row) for row in rows]
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "columns": columns,
            "rows": row_list,
            "row_count": len(row_list),
            "execution_time_ms": round(elapsed_ms, 2),
            "truncated": truncated,
        }

    except sqlite3.OperationalError as e:
        err_msg = str(e)
        if "readonly" in err_msg.lower() or "attempt to write" in err_msg.lower():
            raise ReadOnlyViolationError(f"Database write rejected: {err_msg}") from e
        raise DatabaseError(f"SQLite operational error: {err_msg}") from e
    except sqlite3.Error as e:
        raise DatabaseError(f"SQLite error: {str(e)}") from e
    finally:
        if conn:
            conn.close()


def get_table_names(db_path: str | Path) -> List[str]:
    """Return all non-internal user table names in SQLite database."""
    result = execute_query(
        db_path,
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;",
        read_only=True,
    )
    return [row[0] for row in result["rows"]]


def get_table_schema(db_path: str | Path, table_name: str) -> List[Dict[str, Any]]:
    """Return column specifications for a specific table."""
    conn = get_connection(db_path, read_only=True)
    try:
        cursor = conn.cursor()
        # Sanitize table_name against sqlite_master
        tables = get_table_names(db_path)
        if table_name not in tables:
            raise ValueError(f"Table '{table_name}' does not exist in database.")

        cursor.execute(f"PRAGMA table_info('{table_name}');")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "default_value": row[4],
                "pk": bool(row[5]),
            })
        return columns
    finally:
        conn.close()


def get_foreign_keys(db_path: str | Path, table_name: str) -> List[Dict[str, Any]]:
    """Return foreign key definitions for a table."""
    conn = get_connection(db_path, read_only=True)
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
        fks = []
        for row in cursor.fetchall():
            fks.append({
                "id": row[0],
                "seq": row[1],
                "table": row[2],
                "from": row[3],
                "to": row[4],
                "on_update": row[5],
                "on_delete": row[6],
                "match": row[7],
            })
        return fks
    finally:
        conn.close()


def get_database_schema_dict(db_path: str | Path) -> Dict[str, List[Dict[str, Any]]]:
    """Return full schema dictionary for all user tables."""
    tables = get_table_names(db_path)
    schema = {}
    for table in tables:
        schema[table] = get_table_schema(db_path, table)
    return schema
