"""Metrics for the Text-to-SQL evaluation.

Execution accuracy is measured with a transparent, column-order/naming-insensitive
comparison: the generated result must have the same row count as the gold result,
and every (rounded) value in the gold result must appear in the generated result
with at least the same multiplicity. This tolerates extra id columns and different
column aliases while still requiring the correct answer values.
"""
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

# Approximate USD per 1M tokens (input, output). Adjust as prices change.
PRICES: Dict[str, Tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
    "gemini-2.5-flash": (0.15, 0.60),
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
}


def _norm(value: Any) -> Any:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    return str(value).strip().lower()


def _value_counter(rows: List[Dict[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for row in rows:
        for value in row.values():
            counter[_norm(value)] += 1
    return counter


def results_match(gold_rows: List[Dict[str, Any]], gen_rows: Optional[List[Dict[str, Any]]]) -> bool:
    """True when the generated result matches gold (same row count; gold values ⊆ generated values)."""
    if gen_rows is None:
        return False
    if len(gold_rows) != len(gen_rows):
        return False
    gold_counts = _value_counter(gold_rows)
    gen_counts = _value_counter(gen_rows)
    return all(gen_counts.get(value, 0) >= count for value, count in gold_counts.items())


def estimate_cost(model_id: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    """Estimated USD cost for a call, or None if the model isn't in the price table."""
    if model_id not in PRICES:
        return None
    in_price, out_price = PRICES[model_id]
    return (input_tokens / 1_000_000) * in_price + (output_tokens / 1_000_000) * out_price
