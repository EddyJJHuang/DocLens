import logging
from typing import List
from langchain_openai import OpenAIEmbeddings
from app.config import settings

logger = logging.getLogger(__name__)

def get_embeddings_model() -> OpenAIEmbeddings:
    """
    Initializes and returns the canonical OpenAI embeddings interface.
    Defaults to text-embedding-3-small per project requirements.
    Tenacity is used intrinsically by LangChain for robust rete rate limit handling logic.
    """
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        logger.warning("OPENAI_API_KEY implies placeholder format, requests may fail.")
        
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.openai_api_key,
        # Handled intrinsically for 429/500/502/503/504
        max_retries=3, 
    )

def embed_texts_batch(texts: List[str]) -> List[List[float]]:
    """
    Generates deterministic embeddings array. LangChain explicitly batches internal operations automatically.
    """
    embeddings_model = get_embeddings_model()
    try:
        embeddings = embeddings_model.embed_documents(texts)
        logger.info(f"Generated embeddings for {len(texts)} text chunks.")
        return embeddings
    except Exception as e:
        logger.error(f"Error generating embeddings for batch: {e}")
        raise e
