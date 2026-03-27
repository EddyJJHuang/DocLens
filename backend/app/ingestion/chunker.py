import logging
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings

logger = logging.getLogger(__name__)

def chunk_documents(documents: List[Document]) -> List[Document]:
    """
    Takes a list of loaded LangChain Documents and splits them into smaller
    meaningful chunks via RecursiveCharacterTextSplitter.
    Uses configurable environment variables for size and overlap constraint.
    """
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Successfully split {len(documents)} document blobs into {len(chunks)} chunks.")
        
        # Inject standard structural metadata for each chunk (e.g. index/offset references)
        for i, chunk in enumerate(chunks):
            # Preserving existing metadata context from Loader (like source, page bounds)
            chunk.metadata["chunk_index"] = i
            
        return chunks
    except Exception as e:
        logger.error(f"Error chunking documents: {e}")
        raise e
