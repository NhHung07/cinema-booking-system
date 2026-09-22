from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy.engine import make_url


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _csv_values(name: str, default: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in os.getenv(name, default).split(",") if item.strip())


def _int_values(name: str, default: str) -> tuple[int, ...]:
    values = tuple(int(item) for item in _csv_values(name, default))
    if not values or any(value <= 0 for value in values):
        raise ValueError(f"{name} must contain positive integers")
    return values


@dataclass(frozen=True, slots=True)
class BenchmarkConfig:
    base_url: str
    database_url: str
    scenarios: tuple[str, ...]
    load_levels: tuple[int, ...]
    spawn_rate: float
    duration: str
    warmup_duration: str
    warmup_users: int
    repetitions: int
    random_seed: int
    backend_workers: int
    metrics_interval_seconds: float
    server_pid: int | None
    dataset_file: Path
    output_dir: Path | None
    allow_non_postgres: bool

    @classmethod
    def from_env(cls) -> "BenchmarkConfig":
        output_value = os.getenv("BENCH_OUTPUT_DIR")
        server_pid_value = os.getenv("BENCH_SERVER_PID")
        config = cls(
            base_url=os.getenv("BENCH_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/cinema",
            ),
            scenarios=_csv_values("BENCH_SCENARIOS", "catalogue,booking,concurrent"),
            load_levels=_int_values("BENCH_LOAD_LEVELS", "1,10,25,50,100"),
            spawn_rate=float(os.getenv("BENCH_SPAWN_RATE", "10")),
            duration=os.getenv("BENCH_DURATION", "60s"),
            warmup_duration=os.getenv("BENCH_WARMUP_DURATION", "30s"),
            warmup_users=int(os.getenv("BENCH_WARMUP_USERS", "10")),
            repetitions=int(os.getenv("BENCH_REPETITIONS", "3")),
            random_seed=int(os.getenv("BENCH_RANDOM_SEED", "42")),
            backend_workers=int(os.getenv("BENCH_BACKEND_WORKERS", "1")),
            metrics_interval_seconds=float(os.getenv("BENCH_METRICS_INTERVAL", "1")),
            server_pid=int(server_pid_value) if server_pid_value else None,
            dataset_file=Path(
                os.getenv("BENCH_DATASET_FILE", str(PROJECT_ROOT / "benchmark" / ".state" / "dataset.json"))
            ),
            output_dir=Path(output_value) if output_value else None,
            allow_non_postgres=os.getenv("BENCH_ALLOW_NON_POSTGRES", "0") == "1",
        )
        config.validate()
        return config

    def validate(self) -> None:
        allowed_scenarios = {"catalogue", "booking", "concurrent"}
        unknown = set(self.scenarios) - allowed_scenarios
        if unknown:
            raise ValueError(f"Unknown BENCH_SCENARIOS: {sorted(unknown)}")
        if not self.scenarios:
            raise ValueError("At least one BENCH_SCENARIOS value is required")
        if self.spawn_rate <= 0 or self.repetitions <= 0 or self.warmup_users <= 0:
            raise ValueError("spawn rate, repetitions and warm-up users must be positive")
        if self.metrics_interval_seconds <= 0:
            raise ValueError("metrics interval must be positive")
        if self.backend_workers != 1:
            raise ValueError("Phase 1 baseline must run the backend with exactly one worker")
        if not self.database_url.startswith("postgresql") and not self.allow_non_postgres:
            raise RuntimeError(
                "Phase 1 baseline requires PostgreSQL. Set BENCH_ALLOW_NON_POSTGRES=1 only for "
                "tooling tests, and never report that fallback as production-equivalent."
            )

    def public_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["database_url"] = make_url(self.database_url).render_as_string(hide_password=True)
        data["dataset_file"] = str(self.dataset_file)
        data["output_dir"] = str(self.output_dir) if self.output_dir else None
        data["production_equivalent_database"] = self.database_url.startswith("postgresql")
        return data
