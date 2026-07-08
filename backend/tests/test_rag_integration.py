"""End-to-end RAG integration test.

Exercises the real upload -> ingest -> index -> retrieve -> rerank -> stream
pipeline against the configured OpenAI key. Skipped automatically when no key
is configured, so it stays CI-friendly.

Run: pytest tests/test_rag_integration.py -v -s
"""
import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.integration
SESSION_HEADERS = {"X-DocLens-Session": "itest-session-rag"}

SAMPLE_DOC = """# Demand Planning Glossary (Synthetic Sample)

## Safety Stock
Safety stock is buffer inventory held to absorb variability in demand and supply.
For high-reliability suppliers, a good rule of thumb is to set safety stock to
roughly 40 percent of average monthly demand.

## Lead Time
Lead time is the number of days between placing a purchase order and receiving
the goods. In this dataset, supplier lead times range from 21 to 90 days.

## Reorder Point
The reorder point equals the safety stock plus the expected demand during the
lead time. When on-hand inventory drops to the reorder point, a replenishment
order is triggered.
"""


def _parse_sse(body: str):
    tokens, citations, errors = [], [], []
    for line in body.splitlines():
        if not line.startswith("data: "):
            continue
        frame = json.loads(line[len("data: "):])
        if frame["type"] == "token":
            tokens.append(frame["content"])
        elif frame["type"] == "citations":
            citations = frame["citations"]
        elif frame["type"] == "error":
            errors.append(frame.get("message", "unknown error"))
    return "".join(tokens), citations, errors


@pytest.mark.skipif(not settings.openai_configured, reason="requires a real OPENAI_API_KEY")
def test_upload_and_query_end_to_end() -> None:
    with TestClient(app) as client:
        # 1. Upload a sample markdown document (background ingestion runs
        #    synchronously under TestClient, so it completes before we return).
        upload = client.post(
            "/api/upload",
            headers=SESSION_HEADERS,
            files={"file": ("glossary.md", SAMPLE_DOC.encode("utf-8"), "text/markdown")},
        )
        assert upload.status_code == 200, upload.text
        doc_id = upload.json()["id"]

        # 2. Ingestion should have completed and the index should be live.
        docs = client.get("/api/documents", headers=SESSION_HEADERS).json()
        status = next((d["status"] for d in docs if d["id"] == doc_id), "missing")
        assert status == "completed", f"expected completed ingestion, got: {status}"

        # 3. Ask a question whose answer is grounded in the uploaded doc.
        resp = client.get(
            "/api/query",
            headers=SESSION_HEADERS,
            params={"q": "What is safety stock and how large should it be?", "conversation_id": "itest"},
        )
        assert resp.status_code == 200, resp.text
        answer, citations, errors = _parse_sse(resp.text)

        assert not errors, f"stream reported errors: {errors}"
        assert answer.strip(), "expected a non-empty streamed answer"
        assert citations, "expected at least one citation"
        assert any("glossary.md" in c["source"] for c in citations)

        print("\n--- E2E RAG ANSWER ---")
        print(answer.strip())
        print(f"--- citations: {[c['source'] for c in citations]} ---")
