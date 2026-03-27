import logging
from langchain.retrievers import EnsembleRetriever
from langchain_core.retrievers import BaseRetriever
from app.config import settings

logger = logging.getLogger(__name__)

def get_hybrid_retriever(dense_retriever: BaseRetriever, sparse_retriever: BaseRetriever) -> EnsembleRetriever:
    """
    Instantiates an EnsembleRetriever wrapping the FAISS (Dense) and BM25 (Sparse) retrievers.
    It executes both concurrently and merges the results utilizing the Reciprocal Rank Fusion algorithm.
    Weights dictate the bias towards each underlying retriever.
    """
    logger.info(
        f"Initializing Hybrid Retrieval with Dense={settings.hybrid_dense_weight} | Sparse={settings.hybrid_sparse_weight}"
    )
    
    try:
        ensemble_retriever = EnsembleRetriever(
            retrievers=[dense_retriever, sparse_retriever],
            weights=[settings.hybrid_dense_weight, settings.hybrid_sparse_weight]
        )
        return ensemble_retriever
    except Exception as e:
        logger.error(f"Failed to configure hybrid EnsembleRetriever: {e}")
        raise e
