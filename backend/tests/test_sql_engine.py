import sqlite3

import pytest

from app.database.engine import _connect_readonly, get_schema_dump, run_readonly_query
from app.sql.guard import SqlValidationError


def test_schema_dump_includes_all_tables() -> None:
    schema = get_schema_dump()
    for table in ["regions", "suppliers", "products", "sales_history", "inventory", "demand_forecasts"]:
        assert table in schema
    assert "CREATE TABLE" in schema.upper()


def test_run_query_returns_columns_and_rows() -> None:
    result = run_readonly_query("SELECT name, category FROM products")
    assert result["columns"] == ["name", "category"]
    assert result["row_count"] > 0
    assert set(result["rows"][0].keys()) == {"name", "category"}


def test_row_cap_is_enforced() -> None:
    result = run_readonly_query("SELECT * FROM sales_history", max_rows=10)
    assert result["row_count"] == 10


def test_write_statement_is_blocked_before_execution() -> None:
    with pytest.raises(SqlValidationError):
        run_readonly_query("DELETE FROM products")


def test_readonly_connection_rejects_writes_at_driver_level() -> None:
    # Defense in depth: even bypassing the guard, the connection is read-only.
    conn = _connect_readonly()
    try:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE hack (x INTEGER)")
    finally:
        conn.close()
