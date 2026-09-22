from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from locust import task
from locust.exception import StopUser

from benchmark.scenarios.base import DatasetHttpUser
from benchmark.scenarios.outcomes import classify_concurrent_status


CONCURRENT_OUTCOMES: Counter[str] = Counter()


def write_concurrent_outcomes(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(CONCURRENT_OUTCOMES), indent=2), encoding="utf-8")


class ConcurrentBookingUser(DatasetHttpUser):
    """Workload C: mọi virtual user tranh cùng một seat đúng một lần."""

    weight = 1
    wait_time = lambda _self: 0  # noqa: E731

    def on_start(self) -> None:
        super().on_start()
        self.token = self.login()
        self.attempted = False

    @task
    def compete_for_same_seat(self) -> None:
        if self.attempted or not self.token:
            raise StopUser()
        self.attempted = True
        target = self.dataset["concurrent_target"]
        with self.client.post(
            "/bookings",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"showtime_id": target["showtime_id"], "seat_ids": [target["seat_id"]]},
            name="POST /bookings [same seat race]",
            catch_response=True,
        ) as response:
            outcome = classify_concurrent_status(response.status_code)
            CONCURRENT_OUTCOMES[outcome] += 1
            if outcome == "expected_conflict":
                response.success()
            elif outcome == "unexpected_failure":
                response.failure(f"unexpected HTTP {response.status_code}; expected 201 or 409")
        raise StopUser()


def outcome_file_from_env() -> Path | None:
    value = os.getenv("BENCH_CONCURRENCY_OUTCOME_FILE")
    return Path(value) if value else None
