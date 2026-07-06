"""Multi-LLM Text-to-SQL evaluation runner.

For each configured model, generate SQL for every eval question (with the same
schema + schema-aware few-shot context the app uses), execute it read-only, and
score execution accuracy, valid-SQL rate, latency, and estimated cost. Writes a
leaderboard to evaluation/results/ (Markdown + JSON).

Run:  python -m evaluation.run_eval
"""
import os

# faiss, torch, and grpc each bundle an OpenMP runtime; on macOS the duplicate
# load aborts the process. Allow the duplicate for this offline eval script
# (the production server doesn't hit this). Must be set before heavy imports.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List

from app.database.engine import DB_PATH, get_schema_dump, run_readonly_query
from app.database.knowledge import retrieve_schema_context
from app.database.seed import seed_database
from app.sql.guard import SqlValidationError
from app.sql.text_to_sql import SQL_SYSTEM_PROMPT, _clean_sql
from evaluation.metrics import estimate_cost, results_match
from evaluation.models import available_models

logger = logging.getLogger(__name__)

EVAL_DIR = Path(__file__).resolve().parent
CASES_PATH = EVAL_DIR / "sql_eval.json"
RESULTS_DIR = EVAL_DIR / "results"


def _response_text(resp) -> str:
    content = resp.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content)


def _load_cases() -> List[Dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def _prepare_cases(cases: List[Dict[str, Any]], schema: str) -> List[Dict[str, Any]]:
    """Attach the per-question few-shot context and the gold result set."""
    prepared = []
    for case in cases:
        gold = run_readonly_query(case["gold_sql"])
        prepared.append({
            **case,
            "reference": retrieve_schema_context(case["question"]),
            "gold_rows": gold["rows"],
        })
    return prepared


def _evaluate_model(spec, model, cases: List[Dict[str, Any]], schema: str) -> Dict[str, Any]:
    items = []
    for case in cases:
        system = SQL_SYSTEM_PROMPT.format(schema=schema, reference=case["reference"] or "(none)")
        record = {"id": case["id"], "valid_sql": False, "exec_match": False,
                  "latency_s": None, "input_tokens": 0, "output_tokens": 0, "error": None, "sql": None}
        start = time.perf_counter()
        try:
            resp = model.invoke([("system", system), ("human", case["question"])])
            record["latency_s"] = round(time.perf_counter() - start, 3)
            usage = getattr(resp, "usage_metadata", None) or {}
            record["input_tokens"] = int(usage.get("input_tokens", 0) or 0)
            record["output_tokens"] = int(usage.get("output_tokens", 0) or 0)
            sql = _clean_sql(_response_text(resp))
            record["sql"] = sql
        except Exception as exc:  # provider/network/auth failure
            record["error"] = f"{type(exc).__name__}: {exc}"
            items.append(record)
            continue

        try:
            result = run_readonly_query(sql)
            record["valid_sql"] = True
            record["exec_match"] = results_match(case["gold_rows"], result["rows"])
        except (SqlValidationError, sqlite3.Error) as exc:
            record["error"] = f"exec: {exc}"
        items.append(record)

    return _aggregate(spec, items)


def _aggregate(spec, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(items)
    unavailable = all(it["sql"] is None for it in items)
    valid = sum(1 for it in items if it["valid_sql"])
    correct = sum(1 for it in items if it["exec_match"])
    latencies = [it["latency_s"] for it in items if it["latency_s"] is not None]
    total_in = sum(it["input_tokens"] for it in items)
    total_out = sum(it["output_tokens"] for it in items)
    cost = estimate_cost(spec.model_id, total_in, total_out)
    return {
        "label": spec.label,
        "model_id": spec.model_id,
        "provider": spec.provider,
        "unavailable": unavailable,
        "n": n,
        "exec_accuracy": round(correct / n, 4) if n else 0.0,
        "valid_sql_rate": round(valid / n, 4) if n else 0.0,
        "exec_correct": correct,
        "valid_count": valid,
        "avg_latency_s": round(sum(latencies) / len(latencies), 3) if latencies else None,
        "total_tokens": total_in + total_out,
        "est_cost_usd": round(cost, 5) if cost is not None else None,
        "items": items,
    }


def _write_leaderboard(rows: List[Dict[str, Any]], n_cases: int) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ranked = sorted([r for r in rows if not r["unavailable"]], key=lambda r: r["exec_accuracy"], reverse=True)
    unavailable = [r for r in rows if r["unavailable"]]

    lines = [
        "# DocLens — Text-to-SQL Model Leaderboard",
        "",
        f"Generated on {time.strftime('%Y-%m-%d %H:%M %Z')} from {n_cases} questions over the synthetic demand-planning database.",
        "",
        "Execution accuracy = generated query's result set matches the gold query's "
        "(same row count; gold values are a subset of generated values — tolerant of column aliases/extra id columns).",
        "",
        "| Rank | Model | Exec Accuracy | Valid SQL | Avg Latency (s) | Total Tokens | Est. Cost (USD) |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, r in enumerate(ranked, 1):
        cost = f"${r['est_cost_usd']:.5f}" if r["est_cost_usd"] is not None else "—"
        lat = f"{r['avg_latency_s']:.2f}" if r["avg_latency_s"] is not None else "—"
        lines.append(
            f"| {i} | `{r['label']}` | {r['exec_accuracy']*100:.1f}% ({r['exec_correct']}/{r['n']}) | "
            f"{r['valid_sql_rate']*100:.1f}% | {lat} | {r['total_tokens']:,} | {cost} |"
        )
    if unavailable:
        lines += ["", "**Unavailable (no key / model errored on every call):** " + ", ".join(f"`{r['label']}`" for r in unavailable)]
    lines += ["", "_Numbers are produced by `python -m evaluation.run_eval`; do not edit by hand._", ""]

    (RESULTS_DIR / "sql_leaderboard.md").write_text("\n".join(lines), encoding="utf-8")
    (RESULTS_DIR / "sql_leaderboard.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    logger.info("Wrote leaderboard to %s", RESULTS_DIR)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not DB_PATH.exists():
        seed_database()

    schema = get_schema_dump()
    cases = _prepare_cases(_load_cases(), schema)
    models = available_models()
    if not models:
        print("No models available — configure at least one provider API key in .env.")
        return

    print(f"Evaluating {len(models)} model(s) on {len(cases)} Text-to-SQL questions...\n")
    rows = []
    for spec, model in models:
        print(f"  → {spec.label}")
        rows.append(_evaluate_model(spec, model, cases, schema))

    _write_leaderboard(rows, len(cases))

    print("\n=== Leaderboard ===")
    for r in sorted([r for r in rows if not r["unavailable"]], key=lambda r: r["exec_accuracy"], reverse=True):
        cost = f"${r['est_cost_usd']:.5f}" if r["est_cost_usd"] is not None else "n/a"
        print(f"  {r['label']:32} exec={r['exec_accuracy']*100:5.1f}%  valid={r['valid_sql_rate']*100:5.1f}%  "
              f"lat={r['avg_latency_s']}s  cost={cost}")
    for r in [r for r in rows if r["unavailable"]]:
        print(f"  {r['label']:32} UNAVAILABLE")


if __name__ == "__main__":
    main()
