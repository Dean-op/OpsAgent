from benchmarks.run_rag_benchmark import calculate_summary, source_matches


def test_source_matches_accepts_filename_or_path():
    assert source_matches("cpu_high_usage.md", "uploads/cpu_high_usage.md")
    assert source_matches("cpu_high_usage.md", r"uploads\cpu_high_usage.md")
    assert not source_matches("cpu_high_usage.md", "memory_high_usage.md")


def test_calculate_summary_reports_accuracy_recall_and_latency():
    rows = [
        {
            "expected_source": "cpu_high_usage.md",
            "retrieved_sources": ["cpu_high_usage.md", "memory_high_usage.md"],
            "latency_ms": 100.0,
        },
        {
            "expected_source": "memory_high_usage.md",
            "retrieved_sources": ["cpu_high_usage.md", "memory_high_usage.md"],
            "latency_ms": 300.0,
        },
        {
            "expected_source": "disk_high_usage.md",
            "retrieved_sources": ["cpu_high_usage.md", "memory_high_usage.md"],
            "latency_ms": 500.0,
        },
    ]

    summary = calculate_summary(rows)

    assert summary["total_cases"] == 3
    assert summary["top1_accuracy"] == 1 / 3
    assert summary["recall_at_3"] == 2 / 3
    assert summary["average_latency_ms"] == 300.0
