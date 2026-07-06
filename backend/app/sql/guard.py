"""SQL safety guard.

Validates that an LLM-generated statement is a single, read-only SELECT before
it is ever executed. Validation is done on the parsed AST via sqlglot, not by
string matching, so obfuscated writes (comments, casing, stacked statements)
cannot slip through.
"""
import logging

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

DIALECT = "sqlite"

# Presence of any of these node types anywhere in the tree means the statement
# mutates data or schema (or is an out-of-band command like PRAGMA/ATTACH, which
# sqlglot parses as exp.Command). Reject outright.
_FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.TruncateTable, exp.Command, exp.Set, exp.Merge,
)
# The top-level statement must be one of these read-only shapes.
_ALLOWED_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except, exp.Subquery)


class SqlValidationError(ValueError):
    """Raised when a statement is not a single, safe, read-only SELECT."""


def _enforce_limit(expr: exp.Expression, max_rows: int) -> exp.Expression:
    """Ensure a plain SELECT has a LIMIT; leave other shapes to the executor cap."""
    if isinstance(expr, exp.Select) and expr.args.get("limit") is None:
        return expr.limit(max_rows)
    return expr


def sanitize_select(sql: str, max_rows: int = 200) -> str:
    """Validate and normalize a read-only SELECT.

    Returns the sanitized SQL (with an enforced LIMIT for un-limited plain
    selects). Raises SqlValidationError on anything that is not a single
    read-only query. The executor still applies a hard row cap as defense in depth.
    """
    cleaned = (sql or "").strip().rstrip(";").strip()
    if not cleaned:
        raise SqlValidationError("Empty SQL statement.")

    try:
        statements = [s for s in sqlglot.parse(cleaned, read=DIALECT) if s is not None]
    except Exception as exc:  # sqlglot.errors.ParseError and friends
        raise SqlValidationError(f"Could not parse SQL: {exc}") from exc

    if len(statements) != 1:
        raise SqlValidationError("Only a single SQL statement is allowed.")

    expr = statements[0]
    if not isinstance(expr, _ALLOWED_ROOTS):
        raise SqlValidationError(
            f"Only read-only SELECT queries are allowed (got {type(expr).__name__})."
        )

    forbidden = next(iter(expr.find_all(*_FORBIDDEN_NODES)), None)
    if forbidden is not None:
        raise SqlValidationError(
            f"Statement contains a forbidden operation: {type(forbidden).__name__}."
        )

    return _enforce_limit(expr, max_rows).sql(dialect=DIALECT)
