import logging
from typing import List
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder
from app.config import settings

logger = logging.getLogger(__name__)

# Global singleton cached instance for the CrossEncoder to prevent reloading on each query
_cross_encoder_model = None

def get_cross_encoder() -> CrossEncoder:
    """
    Loads and caches the designated local HuggingFace cross-encoder model for re-ranking.
    """
    global _cross_encoder_model
    if _cross_encoder_model is None:
        logger.info(f"Loading/Initializing CrossEncoder model: {settings.reranker_model_name}...")
        _cross_encoder_model = CrossEncoder(settings.reranker_model_name, max_length=512)
        logger.info("CrossEncoder model loaded successfully.")
    return _cross_encoder_model

def rerank_documents(query: str, documents: List[Document], top_k: int = 5) -> List[Document]:
    """
    Scores hybrid candidate documents against the text query.
    Return top K documents sorted descendingly by relevance score.
    """
    if not documents:
        return []

    logger.info(f"CrossEncoder Re-ranking {len(documents)} candidate chunks for query: '{query}'")
    try:
        encoder = get_cross_encoder()
        
        # CrossEncoder scoring expects lists of (Query, Document Content)
        pairs = [(query, doc.page_content) for doc in documents]
        
        # Predict relevancy confidence scores [0.0 - 1.0 logic depending on CrossEncoder mapping]
        scores = encoder.predict(pairs)
        
        # Map original documents with their computed score
        for i, doc in enumerate(documents):
            # Annotate metadata for React UI usage (citations view)
            doc.metadata["relevance_score"] = float(scores[i])
            
        # Sort aggressively from highest to lowest matching scores
        ranked_pairs = sorted(zip(scores, documents), key=lambda x: x[0], reverse=True)
        
        # Cutoff returning at Top-K to fit token limits gracefully
        ranked_docs = [doc for _, doc in ranked_pairs[:top_k]]
        return ranked_docs
    except Exception as e:
        logger.error(f"CrossEncoder prediction failed: {e}. Falling back to default order.")
        # Do not degrade the application on reranker failure, just return original truncated results
        return documents[:top_k]
