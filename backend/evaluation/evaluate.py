import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.retrieval.bm25 import load_bm25_retriever
from app.retrieval.hybrid import get_hybrid_retriever
from app.retrieval.reranker import rerank_documents
from app.retrieval.vector_store import load_faiss_index


EVALUATION_DIR = Path(__file__).resolve().parent
DEFAULT_DATASET = EVALUATION_DIR / "eval_dataset.json"
RESULTS_DIR = EVALUATION_DIR / "results"


def load_dataset(path: Path) -> list[dict[str, Any]]:
    """Load the benchmark dataset from JSON."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Evaluation dataset must be a list of question records.")
    return data


def contains_expected_chunk(record: dict[str, Any], documents: list[Any]) -> bool:
    """Check whether retrieved chunks contain any configured relevance marker."""
    markers = [str(marker).lower() for marker in record.get("relevant_chunks", [])]
    if not markers:
        source_doc = str(record.get("source_doc", "")).lower()
        return any(source_doc in str(doc.metadata.get("source", "")).lower() for doc in documents)

    retrieved_text = "\n".join(doc.page_content.lower() for doc in documents)
    return any(marker in retrieved_text for marker in markers)


def evaluate(dataset_path: Path, top_k: int) -> pd.DataFrame:
    """Run retrieval relevance checks against the persisted FAISS and BM25 indexes."""
    records = load_dataset(dataset_path)
    vectorstore = load_faiss_index()
    bm25_retriever = load_bm25_retriever()
    dense_retriever = vectorstore.as_retriever(search_kwargs={"k": max(top_k * 2, 10)})
    hybrid_retriever = get_hybrid_retriever(dense_retriever, bm25_retriever)

    rows = []
    for record in records:
        candidates = hybrid_retriever.invoke(record["question"])
        top_docs = rerank_documents(record["question"], candidates, top_k=top_k)
        rows.append(
            {
                "question": record["question"],
                "source_doc": record.get("source_doc", ""),
                "retrieval_hit": contains_expected_chunk(record, top_docs),
                "retrieved_sources": [
                    Path(str(doc.metadata.get("source", "unknown"))).name for doc in top_docs
                ],
            }
        )

    return pd.DataFrame(rows)


def write_results(results: pd.DataFrame) -> tuple[Path, Path]:
    """Persist evaluation output in JSON and CSV formats."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = RESULTS_DIR / f"retrieval_eval_{timestamp}.json"
    csv_path = RESULTS_DIR / f"retrieval_eval_{timestamp}.csv"

    results.to_json(json_path, orient="records", indent=2)
    results.to_csv(csv_path, index=False)
    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate DocLens retrieval quality.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    results = evaluate(args.dataset, args.top_k)
    json_path, csv_path = write_results(results)
    hit_rate = float(results["retrieval_hit"].mean()) if not results.empty else 0.0

    print(f"Evaluated {len(results)} questions")
    print(f"Top-{args.top_k} retrieval hit rate: {hit_rate:.2%}")
    print(f"JSON results: {json_path}")
    print(f"CSV results: {csv_path}")


if __name__ == "__main__":
    main()
