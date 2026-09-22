from __future__ import annotations

import csv
import threading
from datetime import UTC, datetime
from pathlib import Path

import psutil


METRIC_FIELDS = [
    "timestamp_utc",
    "scenario",
    "users",
    "repetition",
    "system_cpu_percent",
    "system_memory_used_mb",
    "system_memory_percent",
    "app_cpu_percent",
    "app_rss_mb",
]


def _process_tree(pid: int | None) -> list[psutil.Process]:
    if pid is None:
        return []
    try:
        parent = psutil.Process(pid)
        return [parent, *parent.children(recursive=True)]
    except psutil.Error:
        return []


def collect_metrics(
    output_file: Path,
    stop_event: threading.Event,
    *,
    scenario: str,
    users: int,
    repetition: int,
    interval_seconds: float,
    server_pid: int | None,
) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    tracked_processes = {process.pid: process for process in _process_tree(server_pid)}
    for process in tracked_processes.values():
        try:
            process.cpu_percent(interval=None)
        except psutil.Error:
            pass
    psutil.cpu_percent(interval=None)

    with output_file.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_FIELDS)
        writer.writeheader()
        while not stop_event.wait(interval_seconds):
            discovered = _process_tree(server_pid)
            for process in discovered:
                tracked_processes.setdefault(process.pid, process)
            app_cpu = 0.0
            app_rss = 0
            for pid, process in list(tracked_processes.items()):
                try:
                    app_cpu += process.cpu_percent(interval=None)
                    app_rss += process.memory_info().rss
                except psutil.Error:
                    tracked_processes.pop(pid, None)
                    continue
            memory = psutil.virtual_memory()
            writer.writerow(
                {
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "scenario": scenario,
                    "users": users,
                    "repetition": repetition,
                    "system_cpu_percent": f"{psutil.cpu_percent(interval=None):.3f}",
                    "system_memory_used_mb": f"{memory.used / 1024 / 1024:.3f}",
                    "system_memory_percent": f"{memory.percent:.3f}",
                    "app_cpu_percent": f"{app_cpu:.3f}" if server_pid is not None else "",
                    "app_rss_mb": f"{app_rss / 1024 / 1024:.3f}" if server_pid is not None else "",
                }
            )
            handle.flush()
