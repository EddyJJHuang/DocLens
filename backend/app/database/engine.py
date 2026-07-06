"""Read-only access to the synthetic demand-planning database.

Safety layers (defense in depth):
1. The connection is opened read-only at the SQLite driver level (mode=ro).
2. Every query passes through the sqlglot guard (SELECT-only).
3. A watchdog interrupts queries that exceed the statement timeout.
4. Only the first `max_rows` rows are fetched.
"""
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict

from app.config import settings
from app.sql.guard import sanitize_select

logger = logging.getLogger(__name__)

DB_PATH = Path(settings.data_dir) / "doclens.db"
MAX_ROWS = 200
QUERY_TIMEOUT_S = 5.0

# Tables exposed to Text-to-SQL, in a sensible reading order.
TABLES = ["regions", "suppliers", "products", "sales_history", "inventory", "demand_forecasts"]


class DatabaseNotSeededError(FileNotFoundError):
    """Raised when the SQLite database file does not exist yet."""


def _connect_readonly() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise DatabaseNotSeededError(
            f"Database not found at {DB_PATH}. Seed it with: python -m app.database.seed"
        )
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_schema_dump() -> str:
    """Return the CREATE TABLE statements for the exposed tables (prompt context)."""
    conn = _connect_readonly()
    try:
        parts = []
        for table in TABLES:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if row and row[0]:
                parts.append(row[0].strip() + ";")
        return "\n\n".join(parts)
    finally:
        conn.close()


def run_readonly_query(
    sql: str, max_rows: int = MAX_ROWS, timeout_s: float = QUERY_TIMEOUT_S
) -> Dict[str, Any]:
    """Validate and execute a read-only query. Returns columns, rows, and the
    sanitized SQL actually run. Raises SqlValidationError (bad query) or
    sqlite3.Error (execution/timeout)."""
    safe_sql = sanitize_select(sql, max_rows=max_rows)

    conn = _connect_readonly()
    watchdog = threading.Timer(timeout_s, conn.interrupt)
    try:
        watchdog.start()
        cursor = conn.execute(safe_sql)
        columns = [d[0] for d in cursor.description] if cursor.description else []
        rows = [dict(row) for row in cursor.fetchmany(max_rows)]
        return {"sql": safe_sql, "columns": columns, "rows": rows, "row_count": len(rows)}
    finally:
        watchdog.cancel()
        conn.close()
