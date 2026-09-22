from __future__ import annotations

import csv
import json
from pathlib import Path

from benchmark.scripts.aggregate_results import aggregate_manifest


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_aggregation_emits_run_and_summary_statistics(tmp_path: Path) -> None:
    stats = tmp_path / "locust_stats.csv"
    metrics = tmp_path / "metrics.csv"
    outcomes = tmp_path / "outcomes.json"
    _write_csv(
        stats,
        [
            {
                "Type": "",
                "Name": "Aggregated",
                "Request Count": 20,
                "Failure Count": 0,
                "Median Response Time": 12,
                "Average Response Time": 15,
                "Max Response Time": 44,
                "Requests/s": 10,
                "50%": 12,
                "95%": 30,
                "99%": 40,
            }
        ],
    )
    _write_csv(
        metrics,
        [
            {
                "system_cpu_percent": 20,
                "system_memory_used_mb": 1000,
                "app_cpu_percent": 10,
                "app_rss_mb": 120,
            },
            {
                "system_cpu_percent": 40,
                "system_memory_used_mb": 1100,
                "app_cpu_percent": 20,
                "app_rss_mb": 140,
            },
        ],
    )
    outcomes.write_text(
        json.dumps({"created": 1, "expected_conflict": 2, "unexpected_failure": 0}),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "scenario": "concurrent",
                        "users": 2,
                        "repetition": 1,
                        "stats_csv": str(stats),
                        "metrics_csv": str(metrics),
                        "outcome_json": str(outcomes),
                        "database_allocation_count": 1,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    runs_path, summary_path = aggregate_manifest(manifest)

    with runs_path.open(newline="", encoding="utf-8") as handle:
        run = next(csv.DictReader(handle))
    with summary_path.open(newline="", encoding="utf-8") as handle:
        summary = next(csv.DictReader(handle))
    assert float(run["p95_ms"]) == 30
    assert float(run["system_cpu_percent_avg"]) == 30
    assert int(run["expected_conflict_count"]) == 2
    assert run["concurrency_correct"] == "True"
    assert float(summary["requests_per_second_mean"]) == 10
    assert float(summary["p99_ms_mean"]) == 40
    assert summary["concurrency_correct_all"] == "True"
