import os
import logging
from pathlib import Path
from typing import List

from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".html", ".htm"}


def _load_markdown(file_path: str) -> List[Document]:
    """Markdown is already plain text — load it directly (no heavy NLP stack)."""
    text = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    return [Document(page_content=text, metadata={"source": file_path})]


def _load_html(file_path: str) -> List[Document]:
    """Extract readable text from HTML using the stdlib parser (no lxml/NLTK)."""
    raw = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")
    for noise in soup(["script", "style", "noscript"]):
        noise.decompose()
    lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
    text = "\n".join(line for line in lines if line)
    return [Document(page_content=text, metadata={"source": file_path})]


def load_document(file_path: str) -> List[Document]:
    """
    Loads a document (PDF, Markdown, or HTML) from the filesystem based on extension.
    Returns a list of LangChain Document objects preserving page/source metadata.

    PDFs are loaded per page (PyPDF); Markdown/HTML are loaded as a single text
    document, then split downstream by the chunker.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = Path(file_path).suffix.lower()

    try:
        if ext == ".pdf":
            # Uses pypdf under the hood and preserves page_content and page metadata.
            docs = PyPDFLoader(file_path).load()
        elif ext == ".md":
            docs = _load_markdown(file_path)
        elif ext in (".html", ".htm"):
            docs = _load_html(file_path)
        else:
            raise ValueError(f"Unsupported document format explicitly: {ext}")

        logger.info(f"Loaded {len(docs)} pages/elements from {file_path}")
        return docs
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        raise e
