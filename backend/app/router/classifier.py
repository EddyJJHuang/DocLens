"""Lightweight question router.

Classifies each question into one of three routes so a single chat interface can
serve both knowledge sources:
- structured  -> Text-to-SQL over the demand-planning database
- unstructured -> document RAG
- hybrid      -> retrieve docs for context AND query the database
"""
import logging

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

VALID_ROUTES = {"structured", "unstructured", "hybrid"}

ROUTER_PROMPT = """You route questions for a hybrid assistant with two knowledge sources.

1. DOCUMENTS: uploaded PDF/Markdown/HTML files (definitions, guides, glossaries, policies, notes).
2. DATABASE: a demand-planning SQL database with tables regions, suppliers, products,
   sales_history, inventory, demand_forecasts (products, monthly sales & revenue, inventory
   levels, forecasts, supplier lead times and reliability).

Choose exactly one route:
- "structured": answerable by querying the DATABASE — counts, sums, rankings, trends, or any
  specific metric about products / sales / inventory / forecasts / suppliers / regions.
- "unstructured": answerable from the DOCUMENTS — concepts, definitions, explanations, how-to, policy.
- "hybrid": needs BOTH — e.g. explain a concept from the docs AND compute a figure from the database.

Reply with ONLY one word: structured, unstructured, or hybrid."""


def _fallback(has_documents: bool) -> str:
    return "unstructured" if has_documents else "structured"


def classify_route(question: str, has_documents: bool = True) -> str:
    """Return one of structured|unstructured|hybrid. Never raises; falls back sensibly."""
    try:
        llm = ChatOpenAI(model=settings.llm_model, temperature=0.0, api_key=settings.openai_api_key)
        prompt = ChatPromptTemplate.from_messages([("system", ROUTER_PROMPT), ("human", "{question}")])
        raw = (prompt | llm | StrOutputParser()).invoke({"question": question})
        route = raw.strip().lower().split()[0].strip('".,!') if raw.strip() else ""
    except Exception as exc:
        logger.error("Router classification failed: %s", exc)
        return _fallback(has_documents)

    if route not in VALID_ROUTES:
        route = _fallback(has_documents)

    # Can't use documents that don't exist — degrade to a database answer.
    if route in ("unstructured", "hybrid") and not has_documents:
        route = "structured"

    logger.info("Routed question to '%s'", route)
    return route
