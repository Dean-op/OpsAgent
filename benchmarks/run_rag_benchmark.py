"""Run a small RAG retrieval benchmark against the local Milvus knowledge base."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CASES_PATH = ROOT_DIR / "benchmarks" / "rag_cases.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "benchmark_results" / "rag_benchmark_report.json"


def source_matches(expected_source: str, retrieved_source: str) -> bool:
    expected_name = Path(expected_source.replace("\\", "/")).name
    retrieved_name = Path(str(retrieved_source).replace("\\", "/")).name
    return expected_name == retrieved_name


def calculate_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {
            "total_cases": 0,
            "top1_accuracy": 0.0,
            "recall_at_1": 0.0,
            "recall_at_3": 0.0,
            "recall_at_5": 0.0,
            "average_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
        }

    def hit_at(row: dict[str, Any], k: int) -> bool:
        expected = row["expected_source"]
        return any(source_matches(expected, source) for source in row["retrieved_sources"][:k])

    latencies = [float(row["latency_ms"]) for row in rows]
    p95_index = min(len(latencies) - 1, int(len(latencies) * 0.95))
    sorted_latencies = sorted(latencies)

    recall_at_1 = sum(1 for row in rows if hit_at(row, 1)) / total
    return {
        "total_cases": total,
        "top1_accuracy": recall_at_1,
        "recall_at_1": recall_at_1,
        "recall_at_3": sum(1 for row in rows if hit_at(row, 3)) / total,
        "recall_at_5": sum(1 for row in rows if hit_at(row, 5)) / total,
        "average_latency_ms": round(statistics.mean(latencies), 2),
        "p95_latency_ms": round(sorted_latencies[p95_index], 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
    }


def load_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list):
        raise ValueError("Benchmark cases file must contain a JSON array")
    return cases


def extract_source(result: Any) -> str:
    metadata = getattr(result, "metadata", {}) or {}
    return metadata.get("_file_name") or metadata.get("_source") or ""


def run_benchmark(cases_path: Path, output_path: Path, top_k: int) -> dict[str, Any]:
    sys.path.insert(0, str(ROOT_DIR))

    from app.core.milvus_client import milvus_manager
    from app.services.vector_search_service import vector_search_service

    cases = load_cases(cases_path)
    rows: list[dict[str, Any]] = []
    milvus_manager.connect()

    for case in cases:
        start = time.perf_counter()
        results = vector_search_service.search_similar_documents(case["query"], top_k=top_k)
        latency_ms = (time.perf_counter() - start) * 1000

        retrieved = [
            {
                "source": extract_source(result),
                "score": result.score,
                "content_preview": result.content[:160].replace("\n", " "),
            }
            for result in results
        ]
        retrieved_sources = [item["source"] for item in retrieved]

        rows.append(
            {
                "id": case.get("id", ""),
                "query": case["query"],
                "expected_source": case["expected_source"],
                "retrieved_sources": retrieved_sources,
                "retrieved": retrieved,
                "top1_correct": bool(retrieved_sources)
                and source_matches(case["expected_source"], retrieved_sources[0]),
                "hit_at_3": any(
                    source_matches(case["expected_source"], source)
                    for source in retrieved_sources[:3]
                ),
                "hit_at_5": any(
                    source_matches(case["expected_source"], source)
                    for source in retrieved_sources[:5]
                ),
                "latency_ms": round(latency_ms, 2),
            }
        )

    report = {
        "benchmark": "rag_retrieval",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "cases_path": str(cases_path),
        "top_k": top_k,
        "summary": calculate_summary(rows),
        "cases": rows,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RAG retrieval benchmark")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    report = run_benchmark(args.cases, args.output, args.top_k)
    summary = report["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Report written to: {args.output}")


if __name__ == "__main__":
    main()
