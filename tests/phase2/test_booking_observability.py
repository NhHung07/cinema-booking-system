import sqlite3

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import TimeoutError

from app.infrastructure import observability as obs
from experiments.phase2.collect import metric_delta


def test_booking_pool_distinguishes_acquire_hold_and_timeout(monkeypatch):
    engine = create_engine("sqlite://", poolclass=obs.BookingMeasuredPool,
                           pool_size=1, max_overflow=0, pool_timeout=.001,
                           creator=lambda: sqlite3.connect(":memory:"))
    obs.instrument_engine(engine)
    clock = iter([0, .01, .02, .03, .04, .5])
    monkeypatch.setattr(obs, "perf_counter", lambda: next(clock))
    before = obs.metrics_bytes().decode()
    token = obs.booking_scope.set(True)
    try:
        with engine.connect():
            with pytest.raises(TimeoutError):
                engine.connect()
    finally:
        obs.booking_scope.reset(token)
        engine.dispose()
    timing = metric_delta(before, obs.metrics_bytes().decode())["booking_timing"]
    assert timing["acquire:ok"]["count"] == 1
    assert timing["acquire:timeout"]["count"] == 1
    assert timing["hold:ok"]["count"] == 1
    assert timing["hold:ok"]["sum_seconds"] == pytest.approx(.49)
    assert timing["hold:ok"]["p95_upper_ms"] == 500
