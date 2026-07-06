"""Unit tests for schema-knowledge loading/splitting (no API key needed)."""
from app.database.knowledge import _load_knowledge_docs, _split_sections


def test_split_sections_by_h2() -> None:
    text = "# Title\nintro line\n## Alpha\nbody a\n## Beta\nbody b\n"
    docs = _split_sections(text, "x.md")

    assert len(docs) == 3  # intro block + Alpha + Beta
    assert docs[1].page_content.startswith("## Alpha")
    assert all(d.metadata["source"] == "x.md" for d in docs)


def test_knowledge_docs_present_in_repo() -> None:
    docs = _load_knowledge_docs()
    sources = {d.metadata["source"] for d in docs}
    assert {"tables.md", "glossary.md", "query_examples.md"} <= sources
    assert len(docs) > 8  # several sections across the files
