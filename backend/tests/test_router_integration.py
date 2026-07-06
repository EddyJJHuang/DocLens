"""End-to-end routing test through the unified /api/query SSE endpoint.

Requires a real OPENAI_API_KEY (skipped otherwise). Verifies a database
question is routed to Text-to-SQL and a document question to RAG.
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.integration

GLOSSARY = """# Demand Planning Glossary (Synthetic Sample)

## Safety Stock
Safety stock is buffer inventory held to absorb variability in demand and supply.
"""


def _collect(body: str):
    frames = []
    for line in body.splitlines():
        if line.startswith("data: "):
            frames.append(json.loads(line[len("data: "):]))
    return frames


@pytest.mark.skipif(not settings.openai_configured, reason="requires a real OPENAI_API_KEY")
def test_structured_question_routes_to_sql() -> None:
    with TestClient(app) as client:
        resp = client.get("/api/query", params={
            "q": "How many products are there in each category?",
            "conversation_id": "route-sql",
        })
        assert resp.status_code == 200, resp.text
        frames = _collect(resp.text)

        route = next(f["route"] for f in frames if f["type"] == "route")
        assert route in ("structured", "hybrid")

        sql_frame = next((f for f in frames if f["type"] == "sql_result"), None)
        assert sql_frame is not None
        assert sql_frame["sql"].lower().lstrip().startswith("select")

        answer = "".join(f["content"] for f in frames if f["type"] == "token")
        assert answer.strip()
        assert not any(f["type"] == "error" for f in frames)


@pytest.mark.skipif(not settings.openai_configured, reason="requires a real OPENAI_API_KEY")
def test_unstructured_question_routes_to_rag() -> None:
    with TestClient(app) as client:
        client.post("/api/upload", files={"file": ("glossary.md", GLOSSARY.encode(), "text/markdown")})
        resp = client.get("/api/query", params={
            "q": "What does safety stock mean?",
            "conversation_id": "route-rag",
        })
        assert resp.status_code == 200, resp.text
        frames = _collect(resp.text)

        route = next(f["route"] for f in frames if f["type"] == "route")
        assert route in ("unstructured", "hybrid")

        answer = "".join(f["content"] for f in frames if f["type"] == "token")
        assert answer.strip()
        assert any(f["type"] == "citations" for f in frames)
