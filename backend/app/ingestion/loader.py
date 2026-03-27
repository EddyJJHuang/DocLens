import os
import logging
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
)

logger = logging.getLogger(__name__)

def load_document(file_path: str) -> List[Document]:
    """
    Loads a document (PDF, Markdown, or HTML) from the filesystem based on extension.
    Returns a list of LangChain Document objects preserving page/source metadata.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    try:
        if ext == ".pdf":
            # Uses pypdf under the hood and preserves page_content and page properties
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        elif ext == ".md":
            loader = UnstructuredMarkdownLoader(file_path)
            docs = loader.load()
        elif ext in [".html", ".htm"]:
            loader = UnstructuredHTMLLoader(file_path)
            docs = loader.load()
        else:
            raise ValueError(f"Unsupported document format explicitly: {ext}")
            
        logger.info(f"Loaded {len(docs)} pages/elements from {file_path}")
        return docs
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        raise e
