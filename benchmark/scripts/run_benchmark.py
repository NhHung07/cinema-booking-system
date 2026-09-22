from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import threading
import urllib.request
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import psutil

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.infrastructure.database.session import create_session_factory
from benchmark.config import PROJECT_ROOT, BenchmarkConfig
from benchmark.dataset import concurrent_allocation_count, read_dataset
from benchmark.scripts.aggregate_results import aggregate_manifest
from benchmark.scripts.collect_metrics import collect_metrics
from benchmark.scripts.generate_charts import generate_charts
from benchmark.scripts.seed_benchmark import seed_from_config


SCENARIO_CLASSES = {
    "catalogue": "CatalogueUser",
    "booking": "BookingJourneyUser",
    "concurrent": "ConcurrentBookingUser",
}


def _git_sha() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unavailable"


def write_environment(config: BenchmarkConfig, output_dir: Path) -> Path:
    virtual_memory = psutil.virtual_memory()
    details = {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "git_sha": _git_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "operating_system": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
        "cpu": {
            "model": platform.processor() or "unavailable",
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
        },
        "ram_total_mb": round(virtual_memory.total / 1024 / 1024, 2),
        "config": config.public_dict(),
        "measurement_note": (
            "Load generator và backend cùng chạy trên một máy; CPU/RAM là tài nguyên chia sẻ. "
            "Backend được cấu hình một worker."
        ),
    }
    path = output_dir / "environment.json"
    path.write_text(json.dumps(details, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def check_backend(base_url: str) -> None:
    try:
        with urllib.request.urlopen(f"{base_url}/health", timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - thông báo đầy đủ lỗi kết nối CLI
        raise RuntimeError(f"Backend chưa sẵn sàng tại {base_url}/health: {exc}") from exc
    if response.status != 200 or payload.get("status") != "ok":
        raise RuntimeError(f"Health check không hợp lệ: HTTP {response.status}, body={payload}")


def _locust_command(
    config: BenchmarkConfig,
    *,
    scenario: str,
    users: int,
    duration: str,
    csv_prefix: Path,
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "locust",
        "-f",
        str(PROJECT_ROOT / "benchmark" / "locustfile.py"),
        "--headless",
        "--host",
        config.base_url,
        "--users",
        str(users),
        "--spawn-rate",
        str(config.spawn_rate),
        "--run-time",
        duration,
        "--csv",
        str(csv_prefix),
        "--csv-full-history",
        "--only-summary",
        "--exit-code-on-error",
        "0",
        SCENARIO_CLASSES[scenario],
    ]


def run_locust(
    config: BenchmarkConfig,
    *,
    scenario: str,
    users: int,
    duration: str,
    run_dir: Path,
    repetition: int,
    measure: bool,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    prefix = run_dir / "locust"
    outcome_path = run_dir / "concurrent-outcomes.json"
    metrics_path = run_dir / "system-metrics.csv"
    log_path = run_dir / "locust.log"
    environment = os.environ.copy()
    environment.update(
        {
            "BENCH_ACTIVE_SCENARIO": scenario,
            "BENCH_DATASET_FILE": str(config.dataset_file),
            "BENCH_RANDOM_SEED": str(config.random_seed),
            "BENCH_CONCURRENCY_OUTCOME_FILE": str(outcome_path),
        }
    )
    stop_event = threading.Event()
    collector: threading.Thread | None = None
    if measure:
        collector = threading.Thread(
            target=collect_metrics,
            kwargs={
                "output_file": metrics_path,
                "stop_event": stop_event,
                "scenario": scenario,
                "users": users,
                "repetition": repetition,
                "interval_seconds": config.metrics_interval_seconds,
                "server_pid": config.server_pid,
            },
            daemon=True,
        )
        collector.start()

    with log_path.open("w", encoding="utf-8") as log_handle:
        completed = subprocess.run(
            _locust_command(
                config,
                scenario=scenario,
                users=users,
                duration=duration,
                csv_prefix=prefix,
            ),
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    stop_event.set()
    if collector is not None:
        collector.join(timeout=max(config.metrics_interval_seconds * 2, 5))
    if completed.returncode != 0:
        raise RuntimeError(f"Locust thất bại (exit={completed.returncode}); xem {log_path}")

    stats_path = prefix.with_name(f"{prefix.name}_stats.csv")
    history_path = prefix.with_name(f"{prefix.name}_stats_history.csv")
    if not stats_path.exists() or not history_path.exists():
        raise RuntimeError(
            "Locust không tạo đủ artifact CSV; "
            f"stats={stats_path.exists()}, history={history_path.exists()}; xem {log_path}"
        )

    result: dict[str, Any] = {
        "scenario": scenario,
        "users": users,
        "repetition": repetition,
        "stats_csv": str(stats_path.resolve()),
        "history_csv": str(history_path.resolve()),
        "metrics_csv": str(metrics_path.resolve()),
        "outcome_json": str(outcome_path.resolve()) if scenario == "concurrent" else None,
        "log": str(log_path.resolve()),
    }
    return result


def verify_concurrent_result(config: BenchmarkConfig, result: dict[str, Any]) -> None:
    outcome_path = Path(result["outcome_json"])
    if not outcome_path.exists():
        raise RuntimeError(f"Thiếu concurrent outcome: {outcome_path}")
    outcome = json.loads(outcome_path.read_text(encoding="utf-8"))
    minimum_conflicts = 0 if int(result["users"]) == 1 else 1
    session_factory = create_session_factory(config.database_url)
    metadata = read_dataset(config.dataset_file)
    with session_factory() as session:
        allocation_count = concurrent_allocation_count(session, metadata)
    result["database_allocation_count"] = allocation_count
    correct = (
        int(outcome.get("created", 0)) == 1
        and int(outcome.get("expected_conflict", 0)) >= minimum_conflicts
        and int(outcome.get("unexpected_failure", 0)) == 0
        and allocation_count == 1
    )
    if not correct:
        raise AssertionError(
            "Concurrent correctness failed: "
            f"outcome={outcome}, database_allocation_count={allocation_count}, "
            f"minimum_conflicts={minimum_conflicts}"
        )


def execute(config: BenchmarkConfig, *, skip_warmup: bool = False) -> Path:
    check_backend(config.base_url)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (config.output_dir or PROJECT_ROOT / "benchmark" / "results" / timestamp).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_environment(config, output_dir)
    manifest: dict[str, Any] = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "environment": str((output_dir / "environment.json").resolve()),
        "warmup_excluded": True,
        "runs": [],
    }
    manifest_path = output_dir / "manifest.json"

    if not skip_warmup:
        for scenario in config.scenarios:
            seed_from_config(config)
            run_locust(
                config,
                scenario=scenario,
                users=config.warmup_users,
                duration=config.warmup_duration,
                run_dir=output_dir / "warmup" / scenario,
                repetition=0,
                measure=False,
            )

    for scenario in config.scenarios:
        for users in config.load_levels:
            for repetition in range(1, config.repetitions + 1):
                seed_from_config(config)
                run_dir = output_dir / "runs" / scenario / f"users-{users}" / f"rep-{repetition}"
                result = run_locust(
                    config,
                    scenario=scenario,
                    users=users,
                    duration=config.duration,
                    run_dir=run_dir,
                    repetition=repetition,
                    measure=True,
                )
                if scenario == "concurrent":
                    verify_concurrent_result(config, result)
                manifest["runs"].append(result)
                manifest_path.write_text(
                    json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
                )

    _, summary_csv = aggregate_manifest(manifest_path, output_dir)
    generate_charts(summary_csv, output_dir / "charts")
    return output_dir


def _positive_int_csv(value: str) -> tuple[int, ...]:
    values = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not values or any(item <= 0 for item in values):
        raise argparse.ArgumentTypeError("Value must be a comma-separated list of positive integers")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the reproducible Phase 1 baseline")
    parser.add_argument("--scenarios", help="catalogue,booking,concurrent")
    parser.add_argument("--loads", type=_positive_int_csv, help="Example: 1,10,25,50,100")
    parser.add_argument("--spawn-rate", type=float)
    parser.add_argument("--duration")
    parser.add_argument("--warmup-duration")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-warmup", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BenchmarkConfig.from_env()
    overrides: dict[str, object] = {}
    if args.scenarios:
        overrides["scenarios"] = tuple(item.strip() for item in args.scenarios.split(",") if item.strip())
    if args.loads:
        overrides["load_levels"] = args.loads
    if args.spawn_rate is not None:
        overrides["spawn_rate"] = args.spawn_rate
    if args.duration:
        overrides["duration"] = args.duration
    if args.warmup_duration:
        overrides["warmup_duration"] = args.warmup_duration
    if args.repetitions is not None:
        overrides["repetitions"] = args.repetitions
    if args.output:
        overrides["output_dir"] = args.output
    if overrides:
        config = replace(config, **overrides)
        config.validate()
    print(execute(config, skip_warmup=args.skip_warmup))


if __name__ == "__main__":
    main()
