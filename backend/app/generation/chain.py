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
    """Initializes the LLM component (defaults to gpt-4o-mini for efficient generation)."""
    return ChatOpenAI(
        model="gpt-4o-mini",
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

async def stream_qa_answer(question: str, chat_history: List[Any], documents: List[Document]):
    """
    Async generator yielding string tokens natively from OpenAI endpoint stream back to the caller (FastAPI SSE).
    """
    logger.info("Initializing streaming response generation loop...")
    chain = setup_qa_chain()
    
    # Format re-ranked chunks block into the context layout
    context_str = format_docs(documents)
    
    try:
        async for chunk in chain.astream({
            "question": question,
            "chat_history": chat_history,
            "context": context_str
        }):
            yield chunk
    except Exception as e:
        logger.error(f"Error during stream generation: {e}")
        yield f"\n[Error generating response: {str(e)}]"
