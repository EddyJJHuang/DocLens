from langchain_core.documents import Document

from app.retrieval.bm25 import create_bm25_retriever
from app.retrieval.reranker import rerank_documents


def test_bm25_retriever_returns_relevant_document() -> None:
    docs = [
        Document(page_content="FastAPI exposes the DocLens upload endpoint.", metadata={"source": "api.md"}),
        Document(page_content="The React sidebar lists prior conversations.", metadata={"source": "ui.md"}),
        Document(page_content="Evaluation records benchmark scores.", metadata={"source": "eval.md"}),
    ]

    retriever = create_bm25_retriever(docs)
    results = retriever.invoke("upload endpoint")

    assert results
    assert results[0].metadata["source"] == "api.md"


def test_reranker_normalizes_scores_to_unit_interval(monkeypatch) -> None:
    docs = [
        Document(page_content="alpha", metadata={"source": "a.md"}),
        Document(page_content="beta", metadata={"source": "b.md"}),
    ]

    class FakeEncoder:
        def predict(self, pairs):
            return [3.0, -2.0]  # raw logits, not probabilities

    monkeypatch.setattr("app.retrieval.reranker.get_cross_encoder", lambda: FakeEncoder())

    ranked = rerank_documents("query", docs, top_k=2)
    scores = [d.metadata["relevance_score"] for d in ranked]

    assert all(0.0 <= s <= 1.0 for s in scores)          # bounded relevance
    assert ranked[0].metadata["source"] == "a.md"         # higher logit ranks first
    assert scores[0] > scores[1]


def test_reranker_falls_back_when_cross_encoder_fails(monkeypatch) -> None:
    docs = [
        Document(page_content="first", metadata={"source": "one.md"}),
        Document(page_content="second", metadata={"source": "two.md"}),
    ]

    def fail_loader():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr("app.retrieval.reranker.get_cross_encoder", fail_loader)

    assert rerank_documents("query", docs, top_k=1) == [docs[0]]
