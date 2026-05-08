import os
import uuid
import json
import logging
from pathlib import Path
from typing import List, Dict
from fastapi import APIRouter, UploadFile, File, Request, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse

from app.config import settings
from app.ingestion.loader import load_document
from app.ingestion.chunker import chunk_documents
from app.retrieval.vector_store import create_faiss_index, save_faiss_index
from app.retrieval.bm25 import create_bm25_retriever, save_bm25_retriever
from app.retrieval.hybrid import get_hybrid_retriever
from app.retrieval.reranker import rerank_documents
from app.generation.chain import stream_qa_answer
from app.api.schemas import DocumentResponse, MessageBase, SourceCitation

logger = logging.getLogger(__name__)

api_router = APIRouter()

# In-memory session tracking for conversations and doc uploads (as per scope)
conversations_db: Dict[str, List[MessageBase]] = {}
uploaded_documents_db: List[DocumentResponse] = []

UPLOAD_DIR = Path(settings.data_dir) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".md", ".html", ".htm"}

@api_router.post("/upload", response_model=DocumentResponse)
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Accepts document uploads and queues them for indexing processing in the background."""
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if not filename or extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed types: {allowed}")

    try:
        stored_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = UPLOAD_DIR / stored_name
        with file_path.open("wb") as f:
            content = await file.read()
            f.write(content)
            
        doc_id = str(uuid.uuid4())
        doc_resp = DocumentResponse(id=doc_id, filename=filename, status="processing")
        uploaded_documents_db.append(doc_resp)
        
        # Dispatch background ingestion handler to prevent connection blocking
        background_tasks.add_task(process_ingestion, str(file_path), doc_id, request.app, filename)
        
        return doc_resp
    except Exception as e:
        logger.error(f"Upload logic failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def process_ingestion(file_path: str, doc_id: str, app, display_filename: str):
    """Execution Pipeline: Document Loader -> Text Splitter -> Incremental Indexing."""
    try:
        docs = load_document(file_path)
        for doc in docs:
            doc.metadata["source"] = display_filename
        chunks = chunk_documents(docs)
        
        vectorstore = app.state.vectorstore
        
        # Check initial states
        if vectorstore is None:
            vectorstore = create_faiss_index(chunks)
        else:
            vectorstore.add_documents(chunks)
            
        # Due to rank_bm25 internal constraints, appending docs is unreliable, rebuilding is safer.
        # We aggregate all cached chunks securely managed under the FAISS inner dictionary structure
        all_docs = list(vectorstore.docstore._dict.values())
        bm25_retriever = create_bm25_retriever(all_docs)
            
        # Freeze and serialize states to filesystem
        save_faiss_index(vectorstore)
        save_bm25_retriever(bm25_retriever)
        
        # Mutate the global ASGI FastAPI state actively
        app.state.vectorstore = vectorstore
        app.state.bm25_retriever = bm25_retriever
        
        # Register completion
        for doc in uploaded_documents_db:
            if doc.id == doc_id:
                doc.status = "completed"
                break
    except Exception as e:
        logger.error(f"Background ingestion fault on {doc_id}: {e}")
        for doc in uploaded_documents_db:
            if doc.id == doc_id:
                doc.status = "failed"
                break

@api_router.get("/documents", response_model=List[DocumentResponse])
def get_documents():
    return uploaded_documents_db

@api_router.get("/conversations", response_model=Dict[str, List[MessageBase]])
def get_conversations():
    return conversations_db

@api_router.get("/conversations/{conversation_id}", response_model=List[MessageBase])
def get_conversation_history(conversation_id: str):
    return conversations_db.get(conversation_id, [])

@api_router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    if conversation_id in conversations_db:
        del conversations_db[conversation_id]
    return {"status": "deleted"}

@api_router.get("/query")
async def query_documents(request: Request, q: str, conversation_id: str):
    """
    Core Server-Sent Event (SSE) endpoint dynamically yielding standard string packets 
    encompassing tokens initially, followed by metadata (Source Citations).
    """
    if not request.app.state.vectorstore or not request.app.state.bm25_retriever:
        raise HTTPException(status_code=400, detail="Document Database Empty. Please upload a file to initialize FAISS context.")
        
    # Bind hybrid mechanism explicitly scoped to top 10 candidates first
    hybrid_retriever = get_hybrid_retriever(
        request.app.state.vectorstore.as_retriever(search_kwargs={"k": 10}),
        request.app.state.bm25_retriever
    )
    
    hybrid_docs = hybrid_retriever.invoke(q)
    top_docs = rerank_documents(q, hybrid_docs, top_k=5)
    
    # Serialize citations exclusively related to this query iteration
    citations = []
    for doc in top_docs:
        source_name = os.path.basename(doc.metadata.get("source", "Unknown Content"))
        citations.append(SourceCitation(
            source=source_name,
            page=str(doc.metadata.get("page", "")),
            chunk_text=doc.page_content,
            relevance_score=doc.metadata.get("relevance_score", 0.0)
        ))
        
    # Map raw role dictionaries from the internal conversational state tracking
    history = conversations_db.get(conversation_id, [])
    lc_history = [(msg.role, msg.content) for msg in history]
    
    async def sse_generator():
        full_answer = ""
        # 1. Pipeline execution - async yielding standard text fragments mapped securely as JSON SSE nodes
        async for token in stream_qa_answer(q, lc_history, top_docs):
            full_answer += token
            yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
        # 2. Append terminating Citation block
        cits_dict = [c.dict() for c in citations]
        yield f"data: {json.dumps({'type': 'citations', 'citations': cits_dict})}\n\n"
        
        # 3. Cache Context State 
        if conversation_id not in conversations_db:
            conversations_db[conversation_id] = []
        conversations_db[conversation_id].append(MessageBase(role="user", content=q))
        conversations_db[conversation_id].append(MessageBase(role="assistant", content=full_answer, citations=citations))

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
