from collections import Counter

import pytest

from experiments.phase2.config import build_matrix, variant_environment
from experiments.phase2.safety import validate_admin_url, validate_database_name


def test_full_matrix_is_complete_reproducible_and_balances_connection_budget():
    runs = build_matrix("full")
    assert len(runs) == 144
    assert runs == build_matrix("full")
    assert set(Counter((r.scenario, r.users, r.repeat) for r in runs).values()) == {4}
    assert {r.variant for r in runs} == {"A", "B", "C", "D"}
    for name, workers in [("A", 1), ("B", 1), ("C", 2), ("D", 2)]:
        env = variant_environment(name, "run_test")
        assert int(env["DB_POOL_SIZE"]) * workers == 8
        assert env["DB_MAX_OVERFLOW"] == "0"
        assert env["CATALOG_CACHE_ENABLED"] == str(name in {"B", "D"}).lower()


def test_smoke_covers_all_architectures_and_scenarios():
    runs = build_matrix("smoke")
    assert len(runs) == 16
    assert {(r.variant, r.scenario) for r in runs} == {
        (a, s) for a in "ABCD" for s in ["R1", "R2", "R3", "R4"]
    }
    assert all(r.users == 10 and r.warmup == 5 and r.duration == 10 for r in runs)


@pytest.mark.parametrize("name", ["cinema", "postgres", "cinema_phase2_", "cinema_phase2_x;DROP DATABASE cinema", "cinema_phase2_OTHER"])
def test_database_guard_rejects_unowned_or_unsafe_names(name):
    with pytest.raises(ValueError):
        validate_database_name(name, owner="abc123")


def test_database_guard_requires_current_experiment_ownership():
    assert validate_database_name("cinema_phase2_abc123_run1", owner="abc123")
    with pytest.raises(ValueError):
        validate_database_name("cinema_phase2_def456_run1", owner="abc123")


@pytest.mark.parametrize("url", ["postgresql://u:p@remote.example/postgres", "sqlite:///x.db", "postgresql://u:p@127.0.0.1/cinema"])
def test_admin_guard_rejects_remote_or_business_databases(url):
    with pytest.raises(ValueError):
        validate_admin_url(url)


def test_loopback_admin_database_is_allowed():
    assert validate_admin_url("postgresql://u:p@127.0.0.1:35439/postgres")
