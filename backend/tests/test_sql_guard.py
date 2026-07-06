import pytest

from app.sql.guard import SqlValidationError, sanitize_select


def test_plain_select_gets_a_limit_injected() -> None:
    out = sanitize_select("SELECT name FROM products", max_rows=200)
    assert "LIMIT 200" in out.upper()


def test_existing_limit_is_preserved() -> None:
    out = sanitize_select("SELECT name FROM products LIMIT 5", max_rows=200)
    assert "LIMIT 5" in out.upper()
    assert "LIMIT 200" not in out.upper()


def test_join_and_aggregate_select_is_allowed() -> None:
    sql = (
        "SELECT p.name, SUM(s.revenue) AS rev FROM sales_history s "
        "JOIN products p ON p.product_id = s.product_id GROUP BY p.product_id"
    )
    assert sanitize_select(sql).lower().startswith("select")


@pytest.mark.parametrize(
    "bad_sql",
    [
        "INSERT INTO products (name) VALUES ('x')",
        "UPDATE products SET unit_price = 0",
        "DELETE FROM products",
        "DROP TABLE products",
        "ALTER TABLE products ADD COLUMN hacked INT",
        "CREATE TABLE hack (x INT)",
        "PRAGMA table_info(products)",
        "ATTACH DATABASE 'other.db' AS other",
        "SELECT 1; DROP TABLE products",          # stacked statements
        "SELECT * FROM products; DELETE FROM products",
        "",
        "not sql at all ;;;",
    ],
)
def test_non_readonly_or_malformed_is_rejected(bad_sql: str) -> None:
    with pytest.raises(SqlValidationError):
        sanitize_select(bad_sql)


def test_write_hidden_in_cte_is_rejected() -> None:
    # A leading comment / whitespace must not fool the parser.
    with pytest.raises(SqlValidationError):
        sanitize_select("/* comment */ DELETE FROM products WHERE 1=1")
