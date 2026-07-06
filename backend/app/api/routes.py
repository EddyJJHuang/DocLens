import os
import uuid
import json
import asyncio
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
from app.generation.chain import stream_qa_answer, stream_hybrid_answer
from app.database.engine import DatabaseNotSeededError
from app.sql.text_to_sql import answer_question, resolve_sql, astream_summary
from app.router.classifier import classify_route
from app.api.schemas import DocumentResponse, MessageBase, SourceCitation, SqlQueryResponse, SqlPayload

logger = logging.getLogger(__name__)

api_router = APIRouter()

# In-memory session tracking for conversations and doc uploads (as per scope)
conversations_db: Dict[str, List[MessageBase]] = {}
uploaded_documents_db: List[DocumentResponse] = []

UPLOAD_DIR = Path(settings.data_dir) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".md", ".html", ".htm"}


def _sse(payload: dict) -> str:
    """Serializes a payload into a single Server-Sent Events frame."""
    return f"data: {json.dumps(payload)}\n\n"


def _require_openai() -> None:
    """Fail fast at the API boundary when the OpenAI key is not configured."""
    if not settings.openai_configured:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Add it to .env and restart the backend.",
        )


def _retrieve(app, query: str):
    """Hybrid retrieve + rerank; returns (top_docs, citations). Blocking — call via a thread."""
    hybrid_retriever = get_hybrid_retriever(
        app.state.vectorstore.as_retriever(search_kwargs={"k": 10}),
        app.state.bm25_retriever,
    )
    top_docs = rerank_documents(query, hybrid_retriever.invoke(query), top_k=5)
    citations = [
        SourceCitation(
            source=os.path.basename(doc.metadata.get("source", "Unknown Content")),
            page=str(doc.metadata.get("page", "")),
            chunk_text=doc.page_content,
            relevance_score=doc.metadata.get("relevance_score", 0.0),
        )
        for doc in top_docs
    ]
    return top_docs, citations


def _sql_payload(sql_result: dict) -> dict:
    """Frame-safe subset of a resolve_sql() result (no answer/error fields)."""
    return {
        "sql": sql_result["sql"],
        "columns": sql_result["columns"],
        "rows": sql_result["rows"],
        "row_count": sql_result["row_count"],
        "repaired": sql_result["repaired"],
    }

@api_router.post("/upload", response_model=DocumentResponse)
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Accepts document uploads and queues them for indexing processing in the background."""
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if not filename or extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed types: {allowed}")

    # Ingestion embeds chunks, which requires a real OpenAI key — fail fast.
    _require_openai()

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
    Unified SSE endpoint. Each question is routed to document RAG (unstructured),
    Text-to-SQL (structured), or both (hybrid). Frames emitted:
      route -> [sql_result] -> token* -> [citations]   (or a terminal `error`)
    """
    _require_openai()

    app = request.app
    has_documents = bool(app.state.vectorstore and app.state.bm25_retriever)

    # Snapshot conversation history up front (immutable copy for the LLM prompt).
    history = conversations_db.get(conversation_id, [])
    lc_history = [(msg.role, msg.content) for msg in history]

    async def sse_generator():
        try:
            route = await asyncio.to_thread(classify_route, q, has_documents)
        except Exception as exc:  # classifier is defensive, but never let routing crash the stream
            logger.error(f"Routing failed for '{q}': {exc}")
            route = "unstructured" if has_documents else "structured"
        yield _sse({"type": "route", "route": route})

        full_answer = ""
        citations: list = []
        sql_payload = None

        try:
            if route == "structured":
                sql_result = await asyncio.to_thread(resolve_sql, q)
                sql_payload = _sql_payload(sql_result)
                yield _sse({"type": "sql_result", **sql_payload})
                if sql_result["error"]:
                    yield _sse({"type": "error", "message": "I couldn't build a working query for that."})
                    return
                async for token in astream_summary(q, sql_result["sql"], sql_result):
                    full_answer += token
                    yield _sse({"type": "token", "content": token})

            elif route == "hybrid":
                sql_result = await asyncio.to_thread(resolve_sql, q)
                sql_payload = _sql_payload(sql_result)
                yield _sse({"type": "sql_result", **sql_payload})
                docs = []
                if has_documents:
                    docs, citations = await asyncio.to_thread(_retrieve, app, q)
                async for token in stream_hybrid_answer(q, lc_history, docs, sql_result):
                    full_answer += token
                    yield _sse({"type": "token", "content": token})
                if citations:
                    yield _sse({"type": "citations", "citations": [c.model_dump() for c in citations]})

            else:  # unstructured
                if not has_documents:
                    yield _sse({"type": "error", "message": "No documents indexed yet. Upload a file first."})
                    return
                docs, citations = await asyncio.to_thread(_retrieve, app, q)
                async for token in stream_qa_answer(q, lc_history, docs):
                    full_answer += token
                    yield _sse({"type": "token", "content": token})
                yield _sse({"type": "citations", "citations": [c.model_dump() for c in citations]})

        except Exception as exc:
            logger.error(f"Query failed (route={route}) for '{q}': {exc}")
            yield _sse({"type": "error", "message": "The request failed. Please try again."})
            return

        # Persist the completed turn (only on success).
        conversations_db.setdefault(conversation_id, [])
        conversations_db[conversation_id].append(MessageBase(role="user", content=q))
        conversations_db[conversation_id].append(
            MessageBase(
                role="assistant",
                content=full_answer,
                route=route,
                citations=citations or None,
                sql=SqlPayload(**sql_payload) if sql_payload else None,
            )
        )

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@api_router.get("/sql-query", response_model=SqlQueryResponse)
def sql_query(q: str):
    """Text-to-SQL over the structured demand-planning database.

    Returns the natural-language answer, the generated (read-only) SQL, and the
    result rows so the UI can surface the query and a result table.
    """
    _require_openai()
    try:
        result = answer_question(q)
    except DatabaseNotSeededError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # OpenAI / unexpected failures
        logger.error(f"Text-to-SQL failed for '{q}': {exc}")
        raise HTTPException(status_code=500, detail="Text-to-SQL request failed.")
    return SqlQueryResponse(**result)
