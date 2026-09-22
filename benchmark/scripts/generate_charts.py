from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


CHARTS = [
    ("requests_per_second_mean", "Throughput theo concurrency", "Requests/second", "rps.png"),
    ("p95_ms_mean", "p95 latency theo concurrency", "Milliseconds", "p95-latency.png"),
    ("p99_ms_mean", "p99 latency theo concurrency", "Milliseconds", "p99-latency.png"),
    ("failure_rate_percent_mean", "Failure rate theo concurrency", "Percent", "failure-rate.png"),
    ("system_cpu_percent_avg_mean", "System CPU theo concurrency", "Percent", "cpu.png"),
]


def generate_charts(summary_csv: Path, output_dir: Path) -> list[Path]:
    with summary_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("summary.csv không có dữ liệu")
    output_dir.mkdir(parents=True, exist_ok=True)
    scenarios = sorted({row["scenario"] for row in rows})
    generated: list[Path] = []
    for field, title, y_label, filename in CHARTS:
        fig, axis = plt.subplots(figsize=(8, 4.5))
        for scenario in scenarios:
            selected = sorted(
                (row for row in rows if row["scenario"] == scenario),
                key=lambda row: int(row["users"]),
            )
            axis.plot(
                [int(row["users"]) for row in selected],
                [float(row[field]) for row in selected],
                marker="o",
                label=scenario,
            )
        axis.set_title(title)
        axis.set_xlabel("Concurrent users")
        axis.set_ylabel(y_label)
        axis.grid(True, alpha=0.3)
        axis.legend()
        fig.tight_layout()
        output_path = output_dir / filename
        fig.savefig(output_path, dpi=150)
        plt.close(fig)
        generated.append(output_path)
    return generated


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate charts from summary.csv")
    parser.add_argument("summary_csv", type=Path)
    parser.add_argument("output_dir", type=Path)
    arguments = parser.parse_args()
    for chart in generate_charts(arguments.summary_csv, arguments.output_dir):
        print(chart)
