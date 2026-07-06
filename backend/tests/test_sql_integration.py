"""End-to-end Text-to-SQL integration test (requires a real OPENAI_API_KEY)."""
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.sql.text_to_sql import answer_question

pytestmark = pytest.mark.integration


@pytest.mark.skipif(not settings.openai_configured, reason="requires a real OPENAI_API_KEY")
def test_text_to_sql_ranking_question() -> None:
    result = answer_question("Which 3 products have the highest total revenue across all regions?")

    assert result.get("error") is None, result.get("error")
    assert result["sql"].lower().lstrip().startswith("select")
    assert result["row_count"] > 0
    assert result["answer"].strip()

    print("\n--- GENERATED SQL ---")
    print(result["sql"])
    print("--- ANSWER ---")
    print(result["answer"].strip())
    print("--- ROWS (first 3) ---")
    for row in result["rows"][:3]:
        print(row)


@pytest.mark.skipif(not settings.openai_configured, reason="requires a real OPENAI_API_KEY")
def test_sql_query_endpoint() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/sql-query", params={"q": "How many products are in each category?"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["error"] is None
        assert data["sql"].lower().lstrip().startswith("select")
        assert data["row_count"] > 0
        assert data["answer"].strip()
