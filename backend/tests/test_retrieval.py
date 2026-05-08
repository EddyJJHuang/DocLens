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


def test_reranker_falls_back_when_cross_encoder_fails(monkeypatch) -> None:
    docs = [
        Document(page_content="first", metadata={"source": "one.md"}),
        Document(page_content="second", metadata={"source": "two.md"}),
    ]

    def fail_loader():
        raise RuntimeError("model unavailable")

    monkeypatch.setattr("app.retrieval.reranker.get_cross_encoder", fail_loader)

    assert rerank_documents("query", docs, top_k=1) == [docs[0]]
