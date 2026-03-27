import os
import logging
from typing import List
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from app.ingestion.embedder import get_embeddings_model

logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "faiss_index"
)

def create_faiss_index(documents: List[Document]) -> FAISS:
    """
    Creates a FAISS dense vector index from a list of Document chunks.
    """
    logger.info(f"Creating FAISS index from {len(documents)} document chunks...")
    embeddings_model = get_embeddings_model()
    try:
        vectorstore = FAISS.from_documents(documents, embeddings_model)
        logger.info("FAISS index created successfully.")
        return vectorstore
    except Exception as e:
        logger.error(f"Error creating FAISS index: {e}")
        raise e

def save_faiss_index(vectorstore: FAISS, path: str = FAISS_INDEX_PATH):
    """
    Persists the FAISS index files to local disk.
    """
    try:
        os.makedirs(path, exist_ok=True)
        vectorstore.save_local(path)
        logger.info(f"FAISS index state saved locally to {path}.")
    except Exception as e:
        logger.error(f"Error saving FAISS index: {e}")
        raise e

def load_faiss_index(path: str = FAISS_INDEX_PATH) -> FAISS:
    """
    Loads a previously serialized FAISS index from disk.
    allow_dangerous_deserialization is enabled since we trust local files.
    """
    embeddings_model = get_embeddings_model()
    try:
        vectorstore = FAISS.load_local(path, embeddings_model, allow_dangerous_deserialization=True)
        logger.info(f"FAISS index loaded locally from {path}.")
        return vectorstore
    except Exception as e:
        logger.error(f"Error loading FAISS index: {e}. Was the index generated yet?")
        raise FileNotFoundError(f"FAISS index missing at {path}. Run document ingestion first.")
