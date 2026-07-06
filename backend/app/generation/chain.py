import logging
from typing import List, Any
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from app.config import settings

logger = logging.getLogger(__name__)

# System instructions enforcing strict retrieval grounding
SYSTEM_PROMPT = """You are DocLens, a highly capable AI assistant that answers questions based on the provided document context.

Instructions:
1. You MUST answer the user's question ONLY using the information provided in the Context below.
2. If the answer cannot be deduced from the Context, you MUST say exactly: "I don't know based on the provided documents." Do not try to make up an answer.
3. When you use information from the context, you MUST cite the specific source document using brackets with the source name, e.g., [document_name.pdf].
4. Be concise and professional.

Context details:
{context}
"""

def format_docs(docs: List[Document]) -> str:
    """Formats the retrieved documents into a single text block referencing metadata source properties."""
    formatted_chunks = []
    for doc in docs:
        source = doc.metadata.get("source", "Unknown Source")
        # Extract base filename if it's a full path
        if "/" in source or "\\" in source:
            source = source.replace("\\", "/").split("/")[-1]
            
        page = doc.metadata.get("page", "")
        page_ref = f" (Page {page})" if page else ""
        content = doc.page_content.replace("\n", " ").strip()
        formatted_chunks.append(f"Source: [{source}{page_ref}]\nContent: {content}\n")
    return "\n".join(formatted_chunks)

def get_llm(streaming: bool = True) -> ChatOpenAI:
    """Initializes the LLM component (model is configured via settings.llm_model)."""
    return ChatOpenAI(
        model=settings.llm_model,
        temperature=0.0, # Ensures deterministic factual responses
        streaming=streaming,
        api_key=settings.openai_api_key
    )

def setup_qa_chain():
    """
    Constructs the LangChain Expression Language (LCEL) runtime sequence.
    Expects dynamic injection of {'question', 'chat_history', 'context'} args.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}")
    ])
    
    llm = get_llm(streaming=True)
    chain = prompt | llm | StrOutputParser()
    return chain

HYBRID_SYSTEM_PROMPT = """You are DocLens, a hybrid knowledge + data assistant.
Answer the user's question using BOTH sources below:
- DOCUMENT CONTEXT: cite the source inline in brackets, e.g. [glossary.md].
- DATABASE RESULT: quote the relevant figures from the rows.
If one source lacks the information, rely on the other. Be concise and specific,
and do not invent values that are not present in either source.

DOCUMENT CONTEXT:
{context}

DATABASE RESULT:
{db}
"""


def _format_db_for_prompt(sql_result: dict) -> str:
    """Render a SQL result compactly for inclusion in a prompt."""
    preview = sql_result.get("rows", [])[:20]
    return (
        f"SQL:\n{sql_result.get('sql', '')}\n"
        f"Columns: {sql_result.get('columns', [])}\n"
        f"Rows ({sql_result.get('row_count', 0)} total, showing up to 20):\n{preview}"
    )


async def stream_hybrid_answer(question: str, chat_history: List[Any], documents: List[Document], sql_result: dict):
    """Stream an answer grounded in BOTH retrieved documents and a SQL result."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", HYBRID_SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])
    chain = prompt | get_llm(streaming=True) | StrOutputParser()
    async for chunk in chain.astream({
        "question": question,
        "chat_history": chat_history,
        "context": format_docs(documents) if documents else "(no documents available)",
        "db": _format_db_for_prompt(sql_result),
    }):
        yield chunk


async def stream_qa_answer(question: str, chat_history: List[Any], documents: List[Document]):
    """
    Async generator yielding string tokens natively from OpenAI endpoint stream back to the caller (FastAPI SSE).
    """
    logger.info("Initializing streaming response generation loop...")
    chain = setup_qa_chain()
    
    # Format re-ranked chunks block into the context layout
    context_str = format_docs(documents)
    
    # Errors are intentionally propagated (not yielded as answer text) so the
    # API layer can emit a typed SSE `error` frame and avoid persisting a broken
    # answer into conversation history.
    async for chunk in chain.astream({
        "question": question,
        "chat_history": chat_history,
        "context": context_str
    }):
        yield chunk
