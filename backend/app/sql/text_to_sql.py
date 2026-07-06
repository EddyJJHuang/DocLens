"""Natural-language -> SQL over the demand-planning database.

Flow: generate SQL from the question + schema context -> validate + execute
(read-only) -> on failure, feed the error back for exactly one repair attempt
-> summarize the result rows into a natural-language answer.

The generated SQL and the raw rows are always returned so the UI can surface
them the way document citations are surfaced for RAG.
"""
import logging
import re
import sqlite3
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.config import settings
from app.database.engine import run_readonly_query, get_schema_dump
from app.database.knowledge import retrieve_schema_context
from app.sql.guard import SqlValidationError

logger = logging.getLogger(__name__)

MAX_ROWS_IN_ANSWER = 30  # rows shown to the summarizer LLM (full set still returned to UI)

SQL_SYSTEM_PROMPT = """You are a precise data analyst that writes SQLite SQL for a demand-planning database.

Rules:
- Output exactly ONE SQLite SELECT statement and nothing else — no prose, no markdown code fences.
- The query MUST be read-only. Never write INSERT/UPDATE/DELETE or any DDL.
- Use only the tables and columns defined in the schema below.
- Months are stored as 'YYYY-MM-01' text. Use string comparisons for date ranges.
- Prefer explicit column lists, clear JOINs, and meaningful aggregations. Add an ORDER BY and a LIMIT when returning lists.

Database schema:
{schema}

Reference (table/column descriptions, business glossary, and example queries — rely on these to write correct SQL):
{reference}
"""

ANSWER_SYSTEM_PROMPT = """You are a demand-planning analyst. Answer the user's question using ONLY the SQL result rows provided.
Be concise and specific: quote the key numbers. If the result set is empty, say that no matching data was found.
Do not invent columns or values that are not in the results."""


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(model=settings.llm_model, temperature=0.0, api_key=settings.openai_api_key)


def _clean_sql(text: str) -> str:
    """Strip markdown fences / stray prose the model may add around the SQL."""
    fenced = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    return text.strip().rstrip(";").strip()


def generate_sql(question: str, schema: str, reference: str = "", error_context: str = "") -> str:
    """Generate a single SQL statement for the question (optionally repairing a prior failure)."""
    human = "{question}"
    if error_context:
        human = (
            "Your previous SQL failed.\n{error}\n\n"
            "Write a corrected single read-only SELECT for this question: {question}"
        )
    prompt = ChatPromptTemplate.from_messages([("system", SQL_SYSTEM_PROMPT), ("human", human)])
    chain = prompt | _make_llm() | StrOutputParser()
    raw = chain.invoke({
        "schema": schema,
        "reference": reference or "(none)",
        "question": question,
        "error": error_context,
    })
    return _clean_sql(raw)


def _execute_with_repair(question: str, schema: str, reference: str, sql: str) -> Dict[str, Any]:
    """Execute `sql`; on validation/execution error, repair once, then execute again."""
    try:
        return run_readonly_query(sql)
    except (SqlValidationError, sqlite3.Error) as first_error:
        logger.warning("Text-to-SQL first attempt failed (%s); repairing once.", first_error)
        repaired_sql = generate_sql(
            question, schema, reference,
            error_context=f"{type(first_error).__name__}: {first_error}\nSQL: {sql}",
        )
        result = run_readonly_query(repaired_sql)
        result["repaired"] = True
        return result


def _summary_context(question: str, sql: str, result: Dict[str, Any]) -> str:
    preview = result["rows"][:MAX_ROWS_IN_ANSWER]
    return (
        f"Question: {question}\n\nSQL:\n{sql}\n\n"
        f"Columns: {result['columns']}\n"
        f"Rows ({result['row_count']} total, showing up to {MAX_ROWS_IN_ANSWER}):\n{preview}"
    )


def _summary_chain():
    prompt = ChatPromptTemplate.from_messages(
        [("system", ANSWER_SYSTEM_PROMPT), ("human", "{context}")]
    )
    return prompt | _make_llm() | StrOutputParser()


def summarize_result(question: str, sql: str, result: Dict[str, Any]) -> str:
    """Turn the result rows into a concise natural-language answer (blocking)."""
    return _summary_chain().invoke({"context": _summary_context(question, sql, result)})


async def astream_summary(question: str, sql: str, result: Dict[str, Any]):
    """Stream the natural-language answer token by token (for the SSE chat)."""
    async for token in _summary_chain().astream({"context": _summary_context(question, sql, result)}):
        yield token


def resolve_sql(question: str) -> Dict[str, Any]:
    """Generate + execute (with one repair). Returns sql/columns/rows/row_count/
    repaired/error but NOT the natural-language answer (the caller streams that)."""
    schema = get_schema_dump()
    reference = retrieve_schema_context(question)  # dynamic few-shot / schema-aware context
    first_sql = generate_sql(question, schema, reference)
    try:
        result = _execute_with_repair(question, schema, reference, first_sql)
        return {
            "sql": result["sql"],
            "columns": result["columns"],
            "rows": result["rows"],
            "row_count": result["row_count"],
            "repaired": result.get("repaired", False),
            "error": None,
        }
    except (SqlValidationError, sqlite3.Error) as exc:
        logger.error("Text-to-SQL failed after repair: %s", exc)
        return {"sql": first_sql, "columns": [], "rows": [], "row_count": 0, "repaired": True, "error": str(exc)}


def answer_question(question: str) -> Dict[str, Any]:
    """Full (blocking) Text-to-SQL pipeline used by the direct endpoint and eval.
    Always returns a dict with answer/sql/rows; graceful message on failure."""
    result = resolve_sql(question)
    if result["error"]:
        return {
            "answer": "I couldn't turn that into a working query over the database. Try rephrasing it.",
            **result,
        }
    answer = summarize_result(question, result["sql"], result)
    return {"answer": answer, **result}
