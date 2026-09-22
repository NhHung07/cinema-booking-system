from __future__ import annotations

import os

from locust import events

from benchmark.scenarios.booking import BookingJourneyUser
from benchmark.scenarios.catalogue import CatalogueUser
from benchmark.scenarios.concurrent_booking import ConcurrentBookingUser
from benchmark.scenarios.concurrent_booking import outcome_file_from_env, write_concurrent_outcomes


@events.quitting.add_listener
def persist_concurrent_outcomes(environment, **_kwargs) -> None:  # type: ignore[no-untyped-def]
    if os.getenv("BENCH_ACTIVE_SCENARIO") != "concurrent":
        return
    output = outcome_file_from_env()
    if output is not None:
        write_concurrent_outcomes(output)


__all__ = ["BookingJourneyUser", "CatalogueUser", "ConcurrentBookingUser"]
