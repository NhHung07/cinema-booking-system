from experiments.phase2.dataset import DatasetSpec, build_manifest, allocation_pair
from experiments.phase2.results import RequestLedger, aggregate_runs
from experiments.phase2.collect import metric_delta


def test_manifest_is_reproducible_and_available_allocations_exclude_background():
    spec = DatasetSpec(users=20, movies=6, rooms=2, seats_per_room=10, showtimes=40, bookings=10)
    first = build_manifest(spec)
    assert first == build_manifest(spec)
    assert len(first["available"]) == 390
    assert len(set(first["available"])) == 390
    assert not set(first["background"]) & set(first["available"])
    for allocation in first["available"]:
        showtime, seat = allocation_pair(allocation, spec)
        assert 1 <= showtime <= 40
        assert ((seat - 1) // 10) == (showtime - 1) % 2


def test_write_partitions_are_disjoint_without_recycling():
    manifest = build_manifest(DatasetSpec(users=20, movies=6, rooms=2, seats_per_room=10, showtimes=40, bookings=10))
    partitions = [set(manifest["available"][i::10]) for i in range(10)]
    assert sum(map(len, partitions)) == len(set.union(*partitions)) == 390


def test_ledger_separates_conflicts_errors_drain_and_successful_bookings():
    ledger = RequestLedger(10, 20)
    ledger.record("write", 11, 12, 201, 1000, expected=201)
    ledger.record("conflict", 12, 13, 409, 1000, expected=409)
    ledger.record("write", 19, 21, 201, 2000, expected=201)
    ledger.record("write", 14, 19, 0, 5000, expected=201)
    ledger.record("read", 9, 11, 200, 2000, expected=200)
    result = ledger.summary()
    assert result["completed_rps"] == .3
    assert result["successful_booking_rps"] == .1
    assert result["unexpected_failures"] == 1
    assert result["requests"] == 4
    assert result["groups"]["write:201"]["count"] == 2
    assert result["groups"]["write:201"]["p95_ms"] == 2000


def test_summary_keeps_invalid_and_missing_runs_visible():
    rows = [{"variant": "A", "scenario": "R1", "users": 10, "valid": True, "completed_rps": value}
            for value in [10, 20, 30]]
    rows.append({"variant": "B", "scenario": "R1", "users": 10, "valid": False, "completed_rps": 1000})
    result = aggregate_runs(rows, expected=144)
    assert result["complete"] is False
    assert result["valid_runs"] == 3
    assert result["invalid_runs"] == 1
    assert result["groups"][0]["completed_rps_median"] == 20


def test_metric_deltas_subtract_warmup_and_merge_worker_counters():
    before = 'cinema_sql_queries_total 1\ncinema_http_requests_total{route="/movies",status="200"} 1\ncinema_cache_operations_total{outcome="hit"} 2\n'
    after = 'cinema_sql_queries_total 9\ncinema_http_requests_total{route="/movies",status="200"} 5\ncinema_cache_operations_total{outcome="hit"} 5\ncinema_cache_operations_total{outcome="miss"} 1\ncinema_cache_operations_total{outcome="write_error"} 2\ncinema_worker_requests_total{pid="10"} 2\ncinema_worker_requests_total{pid="11"} 3\n'
    result = metric_delta(before, after)
    assert result["sql_queries"] == 8
    assert result["sql_per_request"] == 2
    assert result["cache_hit_ratio"] == .75
    assert result["cache_errors"] == 2
    assert result["worker_pids"] == ["10", "11"]
