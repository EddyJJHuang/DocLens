import os
import uuid
import json
import asyncio
import logging
from pathlib import Path
from typing import List
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
from app.session_store import SessionState, session_store

logger = logging.getLogger(__name__)

api_router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".md", ".html", ".htm"}
MAX_UPLOAD_BYTES = settings.max_upload_mb * 1024 * 1024
MAX_SESSION_STORAGE_BYTES = settings.max_session_storage_mb * 1024 * 1024
READ_CHUNK_SIZE = 1024 * 1024
SESSION_HEADER = "X-DocLens-Session"


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


def _get_session(request: Request) -> SessionState:
    session_id = request.headers.get(SESSION_HEADER) or request.query_params.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing DocLens session id.")
    try:
        return session_store.get_or_create(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))


def _validate_query(q: str) -> None:
    if len(q) > settings.max_query_chars:
        raise HTTPException(
            status_code=413,
            detail=f"Question is too long. Limit: {settings.max_query_chars} characters.",
        )


def _retrieve(session: SessionState, query: str):
    """Hybrid retrieve + rerank; returns (top_docs, citations). Blocking — call via a thread."""
    hybrid_retriever = get_hybrid_retriever(
        session.vectorstore.as_retriever(search_kwargs={"k": 10}),
        session.bm25_retriever,
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


async def _save_upload_with_limits(file: UploadFile, target: Path, session: SessionState) -> int:
    total = 0
    try:
        with target.open("wb") as output:
            while True:
                chunk = await file.read(READ_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File is too large. Limit: {settings.max_upload_mb} MB per file.",
                    )
                if session.total_upload_bytes + total > MAX_SESSION_STORAGE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Session upload storage limit reached. "
                            f"Limit: {settings.max_session_storage_mb} MB per session."
                        ),
                    )
                output.write(chunk)
        if total == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        return total
    except Exception:
        target.unlink(missing_ok=True)
        raise


def _remember_turn(
    session: SessionState,
    conversation_id: str,
    question: str,
    answer: str,
    route: str,
    citations: list,
    sql_payload: dict | None,
) -> None:
    if conversation_id not in session.conversations:
        while len(session.conversations) >= settings.max_conversations_per_session:
            oldest_id = next(iter(session.conversations))
            del session.conversations[oldest_id]
        session.conversations[conversation_id] = []

    history = session.conversations[conversation_id]
    history.append(MessageBase(role="user", content=question))
    history.append(
        MessageBase(
            role="assistant",
            content=answer,
            route=route,
            citations=citations or None,
            sql=SqlPayload(**sql_payload) if sql_payload else None,
        )
    )
    if len(history) > settings.max_messages_per_conversation:
        del history[: len(history) - settings.max_messages_per_conversation]

@api_router.post("/upload", response_model=DocumentResponse)
async def upload_document(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Accepts document uploads and queues them for indexing processing in the background."""
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()
    if not filename or extension not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed types: {allowed}")
    session = _get_session(request)
    if len([doc for doc in session.documents if doc.status != "failed"]) >= settings.max_session_uploads:
        raise HTTPException(
            status_code=413,
            detail=f"Too many files in this session. Limit: {settings.max_session_uploads} files.",
        )
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_UPLOAD_BYTES + 2048:
        raise HTTPException(
            status_code=413,
            detail=f"File is too large. Limit: {settings.max_upload_mb} MB per file.",
        )

    # Ingestion embeds chunks, which requires a real OpenAI key — fail fast.
    _require_openai()

    try:
        stored_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = session.uploads_dir / stored_name
        bytes_written = await _save_upload_with_limits(file, file_path, session)
        session.total_upload_bytes += bytes_written
            
        doc_id = str(uuid.uuid4())
        doc_resp = DocumentResponse(id=doc_id, filename=filename, status="processing")
        session.documents.append(doc_resp)
        
        # Dispatch background ingestion handler to prevent connection blocking
        background_tasks.add_task(process_ingestion, str(file_path), doc_id, session.id, filename)
        
        return doc_resp
    except Exception as e:
        logger.error(f"Upload logic failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def process_ingestion(file_path: str, doc_id: str, session_id: str, display_filename: str):
    """Execution Pipeline: Document Loader -> Text Splitter -> Incremental Indexing."""
    session = session_store.get_existing(session_id)
    if session is None:
        Path(file_path).unlink(missing_ok=True)
        return

    try:
        docs = load_document(file_path)
        for doc in docs:
            doc.metadata["source"] = display_filename
        chunks = chunk_documents(docs)
        
        vectorstore = session.vectorstore
        
        # Check initial states
        if vectorstore is None:
            vectorstore = create_faiss_index(chunks)
        else:
            vectorstore.add_documents(chunks)
            
        # Due to rank_bm25 internal constraints, appending docs is unreliable, rebuilding is safer.
        # We aggregate all cached chunks securely managed under the FAISS inner dictionary structure
        all_docs = list(vectorstore.docstore._dict.values())
        bm25_retriever = create_bm25_retriever(all_docs)
            
        # Freeze and serialize states to this session's filesystem cache only.
        save_faiss_index(vectorstore, str(session.faiss_dir))
        save_bm25_retriever(bm25_retriever, str(session.bm25_path))
        
        session.vectorstore = vectorstore
        session.bm25_retriever = bm25_retriever
        
        # Register completion
        for doc in session.documents:
            if doc.id == doc_id:
                doc.status = "completed"
                break
    except Exception as e:
        logger.error(f"Background ingestion fault on {doc_id}: {e}")
        for doc in session.documents:
            if doc.id == doc_id:
                doc.status = "failed"
                break

@api_router.get("/documents", response_model=List[DocumentResponse])
def get_documents(request: Request):
    return _get_session(request).documents

@api_router.get("/conversations", response_model=dict[str, List[MessageBase]])
def get_conversations(request: Request):
    return _get_session(request).conversations

@api_router.get("/conversations/{conversation_id}", response_model=List[MessageBase])
def get_conversation_history(request: Request, conversation_id: str):
    return _get_session(request).conversations.get(conversation_id, [])

@api_router.delete("/conversations/{conversation_id}")
def delete_conversation(request: Request, conversation_id: str):
    conversations = _get_session(request).conversations
    if conversation_id in conversations:
        del conversations[conversation_id]
    return {"status": "deleted"}


@api_router.post("/session/end")
async def end_session(request: Request):
    session_id = request.headers.get(SESSION_HEADER) or request.query_params.get("session_id")
    if not session_id:
        try:
            payload = await request.json()
            session_id = payload.get("session_id")
        except Exception:
            session_id = None
    if not session_id:
        return {"status": "ignored"}
    session_store.end(session_id)
    return {"status": "deleted"}

@api_router.get("/query")
async def query_documents(request: Request, q: str, conversation_id: str):
    """
    Unified SSE endpoint. Each question is routed to document RAG (unstructured),
    Text-to-SQL (structured), or both (hybrid). Frames emitted:
      route -> [sql_result] -> token* -> [citations]   (or a terminal `error`)
    """
    _require_openai()
    _validate_query(q)

    session = _get_session(request)
    has_documents = bool(session.vectorstore and session.bm25_retriever)

    # Snapshot conversation history up front (immutable copy for the LLM prompt).
    history = session.conversations.get(conversation_id, [])
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
                    docs, citations = await asyncio.to_thread(_retrieve, session, q)
                async for token in stream_hybrid_answer(q, lc_history, docs, sql_result):
                    full_answer += token
                    yield _sse({"type": "token", "content": token})
                if citations:
                    yield _sse({"type": "citations", "citations": [c.model_dump() for c in citations]})

            else:  # unstructured
                if not has_documents:
                    yield _sse({"type": "error", "message": "No documents indexed yet. Upload a file first."})
                    return
                docs, citations = await asyncio.to_thread(_retrieve, session, q)
                async for token in stream_qa_answer(q, lc_history, docs):
                    full_answer += token
                    yield _sse({"type": "token", "content": token})
                yield _sse({"type": "citations", "citations": [c.model_dump() for c in citations]})

        except Exception as exc:
            logger.error(f"Query failed (route={route}) for '{q}': {exc}")
            yield _sse({"type": "error", "message": "The request failed. Please try again."})
            return

        # Persist the completed turn (only on success).
        _remember_turn(session, conversation_id, q, full_answer, route, citations, sql_payload)

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
