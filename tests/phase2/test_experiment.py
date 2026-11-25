from collections import Counter

import pytest

from experiments.phase2.config import build_matrix, variant_environment
from experiments.phase2.safety import validate_admin_url, validate_database_name
from experiments.phase2.results import RequestLedger, experiment_summary, booking_overloaded, classify_wave, summarize_waves


def test_followup_matrix_holds_runtime_constant_and_has_two_supported_comparisons():
    for split, variants, count in [(True, {"D0", "D1", "D2"}, 81), (False, {"D0", "D-limit"}, 54)]:
        runs = build_matrix("booking-followup", include_split_auth=split)
        assert len(runs) == count
        assert {r.variant for r in runs} == variants
        assert {r.scenario for r in runs} == {"R2", "R3", "R4"}
        assert all((r.warmup, r.duration, r.drain) == (15, 45, 10) for r in runs)
        assert {r.variant for r in build_matrix("booking-smoke", include_split_auth=split)} == variants
        for variant in variants:
            env = variant_environment(variant, "test")
            assert env["CATALOG_CACHE_ENABLED"] == "true"
            assert env["DB_POOL_SIZE"] == "4"
    assert variant_environment("D1", "test")["BOOKING_SPLIT_AUTH"] == "true"
    assert variant_environment("D2", "test")["BOOKING_MAX_IN_FLIGHT_PER_WORKER"] == "4"
    assert variant_environment("D0", "test")["BOOKING_MAX_IN_FLIGHT_PER_WORKER"] == "0"


def test_admission_and_unexpected_errors_share_a_denominator_but_are_separate():
    ledger = RequestLedger(0, 10)
    assert booking_overloaded("write", 503, {"code": "booking_overloaded"})
    assert not booking_overloaded("read", 503, {"code": "booking_overloaded"})
    assert not booking_overloaded("write", 503, {"code": "other"})
    for status in [201, 409, 503, 503, 500, 0]:
        ledger.record("conflict", 1, 2, status, 1, 201,
                      overloaded=status == 503 and ledger.requests == 2, timed_out=status == 0)
    s = ledger.summary()
    assert s["requests"] == 6
    assert s["unexpected_failures"] == 3
    assert s["booking_rejections"] == 1
    assert s["failure_including_rejections_ratio"] == pytest.approx(4 / 6)
    assert s["successful_booking_ratio"] == pytest.approx(1 / 6)
    assert s["http_500"] == 1 and s["client_timeouts"] == 1
    assert classify_wave({201: 1, 409: 2, "booking_overloaded": 1}, 4) == "winner"
    assert classify_wave({"booking_overloaded": 4}, 4) == "no_winner"
    assert classify_wave({201: 1, 503: 3}, 4) == "unexpected"


def test_followup_completion_is_separate_from_original_phase2():
    spec = [row.to_dict() for row in build_matrix("booking-followup", include_split_auth=False)]
    rows = [dict(row, valid=True) for row in spec]
    meta = dict(matrix=spec, profile="booking-followup", canonical=True)
    assert experiment_summary(meta, rows)["booking_followup_complete"]
    assert not experiment_summary(meta, rows)["primary_complete"]
    assert not experiment_summary(meta, rows[:-1])["booking_followup_complete"]
    assert not experiment_summary(dict(meta, canonical=False), rows)["booking_followup_complete"]


def test_wave_with_a_winner_and_other_errors_counts_in_both_metrics():
    mixed = {"statuses": {201: 1, 500: 2}, "outcome": "unexpected", "started": 1, "finished": 2}
    rejected = {"statuses": {"booking_overloaded": 3}, "outcome": "no_winner", "started": 2, "finished": 3}
    drain = dict(mixed, started=3, finished=5)
    summary = summarize_waves([mixed, rejected, drain], 0, 4)
    assert summary["completed_waves"] == 2
    assert summary["winning_waves_per_second"] == .25
    assert summary["no_winner_wave_ratio"] == .5
    assert summary["unexpected_waves"] == 1


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
