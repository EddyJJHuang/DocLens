# DocLens — Text-to-SQL Model Leaderboard

Generated on 2026-07-06 13:54 PDT from 12 questions over the synthetic demand-planning database.

Execution accuracy = generated query's result set matches the gold query's (same row count; gold values are a subset of generated values — tolerant of column aliases/extra id columns).

| Rank | Model | Exec Accuracy | Valid SQL | Avg Latency (s) | Total Tokens | Est. Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `openai:gpt-4o-mini` | 100.0% (12/12) | 100.0% | 1.71 | 11,726 | $0.00193 |
| 2 | `openai:gpt-4o` | 100.0% (12/12) | 100.0% | 1.08 | 11,704 | $0.03195 |
| 3 | `anthropic:claude-haiku-4-5` | 100.0% (12/12) | 100.0% | 2.56 | 14,272 | $0.01622 |
| 4 | `google:gemini-2.5-flash` | 83.3% (10/12) | 91.7% | 0.84 | 14,431 | $0.00272 |

_Numbers are produced by `python -m evaluation.run_eval`; do not edit by hand._
