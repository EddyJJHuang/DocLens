"""Schema-aware knowledge retrieval for Text-to-SQL (dynamic few-shot).

Builds a dedicated FAISS index over the `db_knowledge/` markdown (table/column
descriptions, business glossary, and example question->SQL pairs). At query time
we retrieve the most relevant sections and inject them into the SQL prompt.

This index is separate from the user-uploaded document index so the two never
pollute each other's retrieval.
"""
import logging
from pathlib import Path
from typing import List

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import settings, PROJECT_ROOT
from app.ingestion.embedder import get_embeddings_model

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = PROJECT_ROOT / "db_knowledge"
INDEX_PATH = str(Path(settings.data_dir) / "db_knowledge_index")
TOP_K = 5

_retriever = None


def _split_sections(text: str, source: str) -> List[Document]:
    """Split markdown into level-2 (`## `) sections so each table/term/example
    is retrievable on its own. Text before the first `## ` is kept as one chunk."""
    sections, current = [], []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [Document(page_content=s, metadata={"source": source}) for s in sections if s.strip()]


def _load_knowledge_docs() -> List[Document]:
    docs: List[Document] = []
    if not KNOWLEDGE_DIR.exists():
        return docs
    for md in sorted(KNOWLEDGE_DIR.glob("*.md")):
        docs.extend(_split_sections(md.read_text(encoding="utf-8"), md.name))
    return docs


def _build_index() -> FAISS:
    docs = _load_knowledge_docs()
    if not docs:
        raise FileNotFoundError(f"No db_knowledge markdown found at {KNOWLEDGE_DIR}")
    vectorstore = FAISS.from_documents(docs, get_embeddings_model())
    vectorstore.save_local(INDEX_PATH)
    logger.info("Built db_knowledge index with %d sections.", len(docs))
    return vectorstore


def get_knowledge_retriever():
    """Cached retriever over the schema-knowledge index (loads or builds it)."""
    global _retriever
    if _retriever is None:
        embeddings = get_embeddings_model()
        try:
            vectorstore = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        except Exception:
            vectorstore = _build_index()
        _retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K})
    return _retriever


def retrieve_schema_context(question: str) -> str:
    """Most relevant schema docs + few-shot examples for a question.
    Returns '' on any failure so SQL generation can degrade to schema-only."""
    try:
        docs = get_knowledge_retriever().invoke(question)
        return "\n\n---\n\n".join(doc.page_content for doc in docs)
    except Exception as exc:
        logger.warning("Schema-knowledge retrieval unavailable: %s", exc)
        return ""
