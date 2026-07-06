# AI-Native Best Practices — DocLens

Findings from building and evaluating DocLens, a hybrid RAG + Text-to-SQL assistant.
**Every number below comes from an actual run of `backend/evaluation/run_eval.py`** against
the synthetic demand-planning database — none are hand-written. Re-run to reproduce.

## Multi-LLM Text-to-SQL leaderboard

12 natural-language questions → SQL → read-only execution → result-set comparison against a gold query.
Each model received the same prompt: the `CREATE TABLE` schema plus dynamically retrieved few-shot
examples (see "Schema-in-context vs. few-shot" below).

| Model | Exec accuracy | Valid SQL | Avg latency | Est. cost (12 q) |
| --- | --- | --- | --- | --- |
| `openai:gpt-4o-mini` | 100.0% (12/12) | 100.0% | 1.71 s | $0.0019 |
| `openai:gpt-4o` | 100.0% (12/12) | 100.0% | 1.08 s | $0.0320 |
| `anthropic:claude-haiku-4-5` | 100.0% (12/12) | 100.0% | 2.56 s | $0.0162 |
| `google:gemini-2.5-flash` | 83.3% (10/12) | 91.7% | 0.84 s | $0.0027 |

Total spend for the full 4-model run: **≈ $0.05**. The live leaderboard artifacts are in
`backend/evaluation/results/`.

> Caveat: 12 questions is a starter set — good enough to surface the patterns below, not a
> production-grade benchmark. Expand `sql_eval.json` before drawing strong conclusions.

## What moved execution accuracy

1. **Schema-in-context is the single biggest lever.** Injecting the exact `CREATE TABLE`
   statements (not a prose description) let every commercial model produce correct JOINs and
   column names. Without it, models hallucinate plausible-but-wrong column names.
2. **Dynamic few-shot beats static examples.** DocLens indexes `db_knowledge/` (table docs,
   a business glossary, and example question→SQL pairs) in a dedicated vector store and retrieves
   the most relevant snippets per question. This is what taught the models domain terms — e.g.
   "stockout risk" maps to `units_on_hand <= reorder_point`, which is defined only in the glossary.
3. **Be explicit about output shape.** "Output exactly ONE SQLite SELECT, no prose, no markdown
   fences" plus a note that months are stored as `'YYYY-MM-01'` strings removed a whole class of
   errors (fenced output, date-format mismatches).
4. **A one-shot self-repair loop recovers transient failures.** On an execution error, feeding the
   DB error + original question back for a single retry fixes most first-attempt mistakes without
   the cost of unbounded retries.

## Robustness findings (from real failures)

- **Models emit stray markup.** `gemini-2.5-flash` appended a `</instruction>` tag to one query.
  A regex fence-stripper plus a **sqlglot AST guard** meant the malformed statement was *rejected*,
  not executed — the guard validates on the parse tree, not string matching, so obfuscated or
  malformed input can't slip through.
- **Execution accuracy is sensitive to result shape.** On "which region sold the most," Gemini
  returned only the region name (omitting the units column), so it didn't match the gold result set.
  For a *user-facing* answer the natural-language summary still answers the question; for
  programmatic result-set matching it counts as a miss. Pick the metric that matches your use case.

## Cost / latency / accuracy tradeoffs

- **`gpt-4o-mini` is the value winner** for Text-to-SQL: 100% accuracy at ~$0.00016/question — 16×
  cheaper than `gpt-4o` for identical accuracy on this set. It's the app default.
- **`gpt-4o`** buys lower latency, not higher accuracy here — reserve it for harder schemas.
- **`claude-haiku-4-5`** matched OpenAI on accuracy; higher latency on this run.
- **`gemini-2.5-flash`** was the fastest and very cheap, but the least reliable at producing clean,
  complete SQL — worth it for latency-critical paths only with strong output validation.

## When to route SQL vs. RAG vs. hybrid

DocLens uses a cheap `gpt-4o-mini` classifier (~$0.00006/call) to route each question:

- **structured** (counts, sums, rankings, trends, any DB metric) → Text-to-SQL.
- **unstructured** (definitions, concepts, how-to, policy) → document RAG.
- **hybrid** (explain a concept *and* compute a figure) → retrieve docs + query DB, answer from both.

The routing call is negligible next to generation, and keeping the two pillars behind one chat
(rather than two UIs) is the whole point: the RAG layer's schema knowledge makes SQL generation
smarter, and the router hides the split from the user.

## Safety (non-negotiable for Text-to-SQL)

- Read-only DB connection (`mode=ro`) — defense in depth beyond the guard.
- sqlglot AST validation: single statement, SELECT-only; reject INSERT/UPDATE/DELETE/DDL/PRAGMA.
- Enforced row cap + statement timeout.
- Never expose DB credentials to the frontend; surface the generated SQL for transparency.

## Reproducing

```bash
cd backend
python -m evaluation.run_eval        # writes results/ + prints the leaderboard
```

Model list and keys come from `.env` / the `EVAL_MODELS` env var; no keys are hardcoded.
