from __future__ import annotations

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


RUN_FIELDS = [
    "scenario",
    "users",
    "repetition",
    "request_count",
    "failure_count",
    "failure_rate_percent",
    "requests_per_second",
    "average_response_time_ms",
    "p50_ms",
    "p95_ms",
    "p99_ms",
    "max_response_time_ms",
    "system_cpu_percent_avg",
    "system_memory_used_mb_avg",
    "app_cpu_percent_avg",
    "app_rss_mb_avg",
    "created_count",
    "expected_conflict_count",
    "unexpected_failure_count",
    "concurrency_correct",
]


def _number(value: object, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _first(row: dict[str, str], names: Iterable[str]) -> str:
    for name in names:
        if name in row and row[name] != "":
            return row[name]
    return ""


def read_locust_aggregate(stats_file: Path) -> dict[str, float]:
    with stats_file.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    aggregate = next((row for row in rows if row.get("Name") == "Aggregated"), None)
    if aggregate is None:
        raise ValueError(f"Không có dòng Aggregated trong {stats_file}")
    request_count = _number(_first(aggregate, ["Request Count", "Requests"]))
    failure_count = _number(_first(aggregate, ["Failure Count", "Failures"]))
    return {
        "request_count": request_count,
        "failure_count": failure_count,
        "failure_rate_percent": failure_count / request_count * 100 if request_count else 0.0,
        "requests_per_second": _number(_first(aggregate, ["Requests/s", "Current RPS"])),
        "average_response_time_ms": _number(_first(aggregate, ["Average Response Time", "Average"])),
        "p50_ms": _number(_first(aggregate, ["50%", "Median Response Time", "Median"])),
        "p95_ms": _number(_first(aggregate, ["95%"])),
        "p99_ms": _number(_first(aggregate, ["99%"])),
        "max_response_time_ms": _number(_first(aggregate, ["Max Response Time", "Max"])),
    }


def read_metric_averages(metrics_file: Path) -> dict[str, float]:
    if not metrics_file.exists():
        return {}
    with metrics_file.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    result: dict[str, float] = {}
    for source, target in (
        ("system_cpu_percent", "system_cpu_percent_avg"),
        ("system_memory_used_mb", "system_memory_used_mb_avg"),
        ("app_cpu_percent", "app_cpu_percent_avg"),
        ("app_rss_mb", "app_rss_mb_avg"),
    ):
        values = [_number(row[source]) for row in rows if row.get(source) not in (None, "")]
        result[target] = statistics.fmean(values) if values else 0.0
    return result


def _read_outcome(path: Path | None) -> dict[str, int]:
    if path is None or not path.exists():
        return {}
    return {key: int(value) for key, value in json.loads(path.read_text(encoding="utf-8")).items()}


def build_run_row(run: dict[str, Any]) -> dict[str, object]:
    row: dict[str, object] = {
        "scenario": run["scenario"],
        "users": int(run["users"]),
        "repetition": int(run["repetition"]),
        **read_locust_aggregate(Path(run["stats_csv"])),
        **read_metric_averages(Path(run["metrics_csv"])),
    }
    outcome = _read_outcome(Path(run["outcome_json"]) if run.get("outcome_json") else None)
    row["created_count"] = outcome.get("created", 0)
    row["expected_conflict_count"] = outcome.get("expected_conflict", 0)
    row["unexpected_failure_count"] = outcome.get("unexpected_failure", 0)
    if run["scenario"] == "concurrent":
        row["concurrency_correct"] = (
            row["created_count"] == 1
            and row["expected_conflict_count"] == max(int(run["users"]) - 1, 0)
            and row["unexpected_failure_count"] == 0
            and int(run.get("database_allocation_count", -1)) == 1
        )
    else:
        row["concurrency_correct"] = ""
    return {field: row.get(field, 0.0) for field in RUN_FIELDS}


def _mean(rows: list[dict[str, object]], field: str) -> float:
    return statistics.fmean(float(row[field]) for row in rows)


def _stdev(rows: list[dict[str, object]], field: str) -> float:
    values = [float(row[field]) for row in rows]
    return statistics.stdev(values) if len(values) > 1 else 0.0


def summarise_runs(run_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, int], list[dict[str, object]]] = defaultdict(list)
    for row in run_rows:
        groups[(str(row["scenario"]), int(row["users"]))].append(row)

    summaries: list[dict[str, object]] = []
    metric_fields = [
        "failure_rate_percent",
        "requests_per_second",
        "average_response_time_ms",
        "p50_ms",
        "p95_ms",
        "p99_ms",
        "max_response_time_ms",
        "system_cpu_percent_avg",
        "system_memory_used_mb_avg",
        "app_cpu_percent_avg",
        "app_rss_mb_avg",
    ]
    for (scenario, users), rows in sorted(groups.items()):
        item: dict[str, object] = {
            "scenario": scenario,
            "users": users,
            "repetitions": len(rows),
            "request_count_total": int(sum(float(row["request_count"]) for row in rows)),
            "failure_count_total": int(sum(float(row["failure_count"]) for row in rows)),
            "created_count_total": int(sum(int(row["created_count"]) for row in rows)),
            "expected_conflict_count_total": int(
                sum(int(row["expected_conflict_count"]) for row in rows)
            ),
            "unexpected_failure_count_total": int(
                sum(int(row["unexpected_failure_count"]) for row in rows)
            ),
            "concurrency_correct_all": (
                all(row["concurrency_correct"] is True for row in rows)
                if scenario == "concurrent"
                else ""
            ),
        }
        for field in metric_fields:
            item[f"{field}_mean"] = _mean(rows, field)
            item[f"{field}_median"] = statistics.median(float(row[field]) for row in rows)
            item[f"{field}_stdev"] = _stdev(rows, field)
        summaries.append(item)
    return summaries


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError("Không có dữ liệu để ghi CSV")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def aggregate_manifest(manifest_path: Path, output_dir: Path | None = None) -> tuple[Path, Path]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    destination = output_dir or manifest_path.parent
    run_rows = [build_run_row(run) for run in manifest["runs"]]
    summary_rows = summarise_runs(run_rows)
    runs_path = destination / "runs.csv"
    summary_path = destination / "summary.csv"
    _write_csv(runs_path, run_rows)
    _write_csv(summary_path, summary_rows)
    (destination / "summary.json").write_text(
        json.dumps(summary_rows, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return runs_path, summary_path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate Phase 1 Locust results")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    _, summary_path = aggregate_manifest(args.manifest, args.output_dir)
    print(summary_path)


if __name__ == "__main__":
    main()
