from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.retrieval.vector_store import load_faiss_index
from app.retrieval.bm25 import load_bm25_retriever
from app.api.routes import api_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup global app.state variables representing the loaded indices context
    try:
        logger.info("Initializing context FAISS vector engine...")
        app.state.vectorstore = load_faiss_index()
        logger.info("Initializing context BM25 retrieval engine...")
        app.state.bm25_retriever = load_bm25_retriever()
    except Exception as e:
        logger.warning(f"Could not load physical indices initially on startup: {e}. Search engines will remain dormant until the first file is ingested via /api/upload.")
        app.state.vectorstore = None
        app.state.bm25_retriever = None
    yield
    # Execution here handles elegant resource shutdown / destruction behaviors

app = FastAPI(title="DocLens API", version="1.0.0", lifespan=lifespan)

# Restrict Origin headers globally depending on environment contexts
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
