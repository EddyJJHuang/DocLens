from langchain_core.documents import Document

from app.ingestion.chunker import chunk_documents
from app.ingestion.loader import load_document


def test_chunk_documents_preserves_metadata() -> None:
    document = Document(
        page_content=("DocLens keeps citations attached to chunks. " * 80).strip(),
        metadata={"source": "sample.md", "page": 1},
    )

    chunks = chunk_documents([document])

    assert len(chunks) > 1
    assert chunks[0].metadata["source"] == "sample.md"
    assert chunks[0].metadata["page"] == 1
    assert chunks[0].metadata["chunk_index"] == 0


def test_load_document_rejects_unsupported_extension(tmp_path) -> None:
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("plain text is not part of the supported upload set")

    try:
        load_document(str(unsupported))
    except ValueError as exc:
        assert "Unsupported document format" in str(exc)
    else:
        raise AssertionError("Expected unsupported extension to raise ValueError")
