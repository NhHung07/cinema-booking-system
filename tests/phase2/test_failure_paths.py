import json
import os
import signal
import sys
import time

import psutil
import pytest

from experiments.phase2.collect import ResourceSampler
from experiments.phase2.config import RunSpec
from experiments.phase2.runner import run_one
from experiments.phase2.runtime import Processes


def test_redis_death_during_warmup_cannot_be_hidden_by_healthy_measurement(tmp_path):
    sampler = ResourceSampler({"api": 100, "redis": 200, "load": 300}, "unused", tmp_path / "resources.csv")
    sampler.samples = [
        {"monotonic": 1, "component": "redis", "process_ids": [], "cpu_percent": 0, "rss_bytes": 0, "process_count": 0},
        {"monotonic": 10, "component": "redis", "process_ids": [200], "cpu_percent": 1, "rss_bytes": 100, "process_count": 1},
        {"monotonic": 10, "component": "api", "process_ids": [100], "cpu_percent": 10, "rss_bytes": 100, "process_count": 1},
        {"monotonic": 10, "component": "load", "process_ids": [300], "cpu_percent": 10, "rss_bytes": 100, "process_count": 1},
    ]
    result = sampler.summary(10, 20)
    assert result["required_service_missing"] == ["redis"]


@pytest.mark.parametrize("creation_fails", [False, True])
def test_invalid_result_is_saved_even_when_database_creation_or_cleanup_fails(tmp_path, monkeypatch, creation_fails):
    class UnavailableAdmin:
        owner = "test"

        def create(self, *args, **kwargs):
            if creation_fails:
                raise OSError("database unavailable during create")
            return "cinema_phase2_test_r001"

        def database_url(self, name):
            return "sqlite://"

        def drop(self, name):
            raise OSError("database unavailable during cleanup")

    def fail_fingerprint(engine):
        raise OSError("database unavailable during verification")

    monkeypatch.setattr("experiments.phase2.runner.database_fingerprint", fail_fingerprint)
    directory = tmp_path / "001"
    result = run_one(UnavailableAdmin(), "snapshot", {"spec": {"bookings": 0}}, {},
                     RunSpec("A", "R1", 10, 1, 1, 1), directory, None, None)
    assert result["valid"] is False
    assert json.loads((directory / "result.json").read_text())["valid"] is False
    assert json.loads((directory / "state.json").read_text())["status"] == "invalid"
    if not creation_fails:
        assert result["cleanup_errors"]


def test_process_group_cleanup_reaps_live_child_after_leader_has_exited(tmp_path):
    manager = Processes()
    pidfile = tmp_path / "child.pid"
    program = (
        "import subprocess,sys,pathlib; "
        "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
        "pathlib.Path(sys.argv[1]).write_text(str(child.pid))"
    )
    leader = manager.start([sys.executable, "-c", program, str(pidfile)], tmp_path / "process.log")
    leader.wait(timeout=5)
    child = psutil.Process(int(pidfile.read_text()))
    assert child.is_running()
    try:
        manager.close()
        deadline = time.monotonic() + 3
        while child.is_running() and child.status() != psutil.STATUS_ZOMBIE and time.monotonic() < deadline:
            time.sleep(.01)
        assert not child.is_running() or child.status() == psutil.STATUS_ZOMBIE
    finally:
        if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
            child.kill()


def test_experiment_summary_survives_database_cleanup_failure(tmp_path):
    from experiments.phase2.runner import finalize_experiment

    class FailedCleanup:
        def close(self):
            raise OSError("database down")

    spec = {"variant": "A", "scenario": "R1", "users": 10, "repeat": 1}
    metadata = {"profile": "smoke", "canonical": False, "matrix": [spec]}
    rows = [dict(spec, valid=True, completed_rps=10)]
    summary = finalize_experiment(FailedCleanup(), tmp_path, metadata, rows)
    assert (tmp_path / "experiment.json").is_file()
    assert (tmp_path / "summary.json").is_file()
    assert json.loads((tmp_path / "experiment.json").read_text())["cleanup_errors"]
    assert summary["complete"] is False


def test_notebook_interrupt_is_forwarded_to_runner_process_group(tmp_path):
    manager = Processes()
    pidfile = tmp_path / "runner.pid"
    child_code = "import os,pathlib,sys,time; pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    command = [sys.executable, "-c", child_code, str(pidfile)]
    wrapper = "from experiments.phase2.notebook import run_checked; run_checked(" + repr(command) + ")"
    parent = manager.start([sys.executable, "-c", wrapper], tmp_path / "notebook.log")
    child = None
    try:
        deadline = time.monotonic() + 5
        while not pidfile.exists() and parent.poll() is None and time.monotonic() < deadline:
            time.sleep(.01)
        assert pidfile.exists(), (tmp_path / "notebook.log").read_text()
        child = psutil.Process(int(pidfile.read_text()))
        parent.send_signal(signal.SIGINT)
        assert parent.wait(timeout=5) != 0
        assert not child.is_running() or child.status() == psutil.STATUS_ZOMBIE
    finally:
        manager.close()
        if child is not None and child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
            child.kill()
