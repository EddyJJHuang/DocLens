import os
import pickle
import logging
from typing import List
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

logger = logging.getLogger(__name__)

BM25_INDEX_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "bm25_index", "bm25_retriever.pkl"
)

def create_bm25_retriever(documents: List[Document]) -> BM25Retriever:
    """
    Creates a sparse BM25 retriever utilizing rank_bm25 tokenizer.
    The internal tokenization preprocessing involves lowercasing and standard text normalization.
    """
    logger.info(f"Creating BM25 index from {len(documents)} document chunks...")
    try:
        retriever = BM25Retriever.from_documents(documents)
        logger.info("BM25 index initialized successfully.")
        return retriever
    except Exception as e:
        logger.error(f"Error creating BM25 index: {e}")
        raise e

def save_bm25_retriever(retriever: BM25Retriever, path: str = BM25_INDEX_PATH):
    """
    Serializes the BM25 model variables directly via standard serialization.
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(retriever, f)
        logger.info(f"BM25 index binary dumped to {path}.")
    except Exception as e:
        logger.error(f"Error saving BM25 index binary: {e}")
        raise e

def load_bm25_retriever(path: str = BM25_INDEX_PATH) -> BM25Retriever:
    """
    Reconstructs the BM25 model state back into an active Retriever.
    """
    try:
        with open(path, "rb") as f:
            retriever = pickle.load(f)
        logger.info(f"BM25 index loaded successfully from {path}.")
        return retriever
    except Exception as e:
        logger.error(f"Error loading BM25 index: {e}. Was the index generated yet?")
        raise FileNotFoundError(f"BM25 index missing at {path}. Run document ingestion first.")
