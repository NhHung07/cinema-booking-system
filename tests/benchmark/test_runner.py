from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from benchmark.config import BenchmarkConfig
from benchmark.scripts import run_benchmark
from benchmark.scripts.run_benchmark import _locust_command, run_locust, verify_concurrent_result


def _config(tmp_path: Path) -> BenchmarkConfig:
    return BenchmarkConfig(
        base_url="http://127.0.0.1:8000",
        database_url="postgresql+psycopg://postgres:postgres@127.0.0.1:5432/cinema",
        scenarios=("catalogue",),
        load_levels=(100,),
        spawn_rate=10,
        duration="60s",
        warmup_duration="30s",
        warmup_users=10,
        repetitions=1,
        random_seed=42,
        backend_workers=1,
        metrics_interval_seconds=1,
        server_pid=None,
        dataset_file=tmp_path / "dataset.json",
        output_dir=tmp_path,
        allow_non_postgres=False,
    )


def test_locust_request_failures_do_not_abort_the_load_matrix(tmp_path: Path) -> None:
    command = _locust_command(
        _config(tmp_path),
        scenario="catalogue",
        users=100,
        duration="60s",
        csv_prefix=tmp_path / "locust",
    )

    option_index = command.index("--exit-code-on-error")
    assert command[option_index + 1] == "0"


def test_run_locust_rejects_missing_csv_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args=args[0], returncode=0),
    )

    with pytest.raises(RuntimeError, match="không tạo đủ artifact CSV"):
        run_locust(
            _config(tmp_path),
            scenario="catalogue",
            users=1,
            duration="1s",
            run_dir=tmp_path / "run",
            repetition=1,
            measure=False,
        )


def test_concurrent_validator_accepts_replacement_user_conflicts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome_path = tmp_path / "outcomes.json"
    outcome_path.write_text(
        json.dumps({"created": 1, "expected_conflict": 34, "unexpected_failure": 0}),
        encoding="utf-8",
    )

    class FakeSession:
        def __enter__(self) -> "FakeSession":
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(run_benchmark, "create_session_factory", lambda _url: FakeSession)
    monkeypatch.setattr(run_benchmark, "read_dataset", lambda _path: {})
    monkeypatch.setattr(run_benchmark, "concurrent_allocation_count", lambda _session, _data: 1)
    result = {"users": 25, "outcome_json": str(outcome_path)}

    verify_concurrent_result(_config(tmp_path), result)

    assert result["database_allocation_count"] == 1
