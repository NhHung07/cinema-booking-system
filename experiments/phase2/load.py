"""Chạy Locust trong tiến trình riêng để gevent không sửa event loop của API/test."""
from gevent import monkey
monkey.patch_all()

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import random
import requests
from socket import timeout as SocketTimeout
from time import perf_counter

import gevent
from gevent.event import Event
from gevent.lock import Semaphore
import jwt
from locust import FastHttpUser, task, constant, constant_pacing
from locust.env import Environment

from experiments.phase2.config import BOOKING_CLIENT_TIMEOUT_SECONDS, BOOKING_USER_PERIOD_SECONDS, BOOKING_VARIANTS, RunSpec, SEED
from experiments.phase2.dataset import DatasetSpec, allocation_pair
from experiments.phase2.environment import write_json
from experiments.phase2.results import RequestLedger, booking_overloaded, classify_wave, summarize_waves


class LoadState:
    def __init__(self, spec: RunSpec, manifest: dict):
        self.spec, self.manifest = spec, manifest
        self.dataset = DatasetSpec(**manifest["spec"])
        self.next_user = 0
        self.gate, self.lock = Event(), Semaphore()
        self.accepting, self.inflight = True, 0
        self.ledger = None
        self.all_statuses = Counter()
        self.acknowledged = 0
        self.errors = []
        self.wave_number, self.waves = 0, []
        self.wave = self.new_wave() if spec.scenario == "R3" else None

    def new_wave(self):
        if self.wave_number >= len(self.manifest["available"]):
            self.errors.append("allocation_exhausted")
            return None
        allocation = self.manifest["available"][self.wave_number]
        self.wave_number += 1
        return {"allocation": allocation, "remaining": self.spec.users,
                "statuses": Counter(), "done": Event(), "started": None}

    def finish_wave(self, wave, status):
        with self.lock:
            wave["statuses"][status] += 1
            wave["remaining"] -= 1
            if wave["remaining"] == 0:
                now = perf_counter()
                outcome = classify_wave(wave["statuses"], self.spec.users)
                if outcome == "multiple_winners":
                    self.errors.append("multiple_successes_for_one_seat")
                if outcome == "no_winner" and wave["statuses"][409]:
                    self.errors.append("conflict_wave_without_winner")
                self.waves.append({"allocation": wave["allocation"], "statuses": dict(wave["statuses"]),
                                   "outcome": outcome, "started": wave["started"], "finished": now})
                self.wave = self.new_wave() if self.accepting else None
                wave["done"].set()


class CinemaUser(FastHttpUser):
    wait_time = constant(0)

    def on_start(self):
        self.state = self.environment.phase2
        self.index = self.state.next_user
        self.state.next_user += 1
        self.sequence, self.read_sequence, self.cycle = 0, 0, self.index % 5
        self.rng = random.Random(SEED + self.index)
        self.token = jwt.encode({"sub": str(self.index + 1), "exp": datetime.now(timezone.utc) + timedelta(hours=12)},
                                os.environ["JWT_SECRET_KEY"], algorithm="HS256")
        self.state.gate.wait()

    def send_request(self, method, path, kind, expected, **kwargs):
        started = perf_counter()
        self.state.inflight += 1
        status, overloaded, timed_out = 0, False, False
        try:
            with self.client.request(method, path, name=kind, catch_response=True, **kwargs) as response:
                status = response.status_code or 0
                timed_out = status == 0 and isinstance(getattr(response, "error", None), (SocketTimeout, gevent.Timeout))
                if status == 503 and kind in {"write", "conflict"}:
                    try:
                        overloaded = booking_overloaded(kind, status, response.json())
                    except ValueError:
                        pass
                if status == expected or (kind == "conflict" and status in {201, 409}):
                    response.success()
                else:
                    response.failure("booking_overloaded" if overloaded else f"unexpected_status_{status}")
                if status == 201:
                    try:
                        if not isinstance(response.json().get("id"), int):
                            self.state.errors.append("invalid_booking_response")
                    except (ValueError, AttributeError):
                        self.state.errors.append("invalid_booking_response")
        finally:
            finished = perf_counter()
            self.state.inflight -= 1
            self.state.all_statuses[status] += 1
            self.state.acknowledged += method == "POST" and status == 201
            if self.state.ledger:
                self.state.ledger.record(kind, started, finished, status, (finished - started) * 1000,
                                         expected, overloaded=overloaded, timed_out=timed_out)
        return "booking_overloaded" if overloaded else status

    def read_catalog(self):
        # A fixed ten-request cycle gives 20/40/30/10 rather than random mix drift.
        choice = self.read_sequence % 10
        self.read_sequence += 1
        movie = self.rng.randint(1, min(50, self.state.dataset.movies))
        if choice < 2:
            path = "/movies"
        elif choice < 6:
            path = f"/movies/{movie}"
        elif choice < 9:
            path = f"/showtimes?movie_id={movie}"
        else:
            path = f"/showtimes?movie_id={movie}&date=2030-01-01"
        self.send_request("GET", path, "read", 200)

    def book_unique(self):
        position = self.index + self.sequence * self.state.spec.users
        self.sequence += 1
        if position >= len(self.state.manifest["available"]):
            self.state.errors.append("allocation_exhausted")
            self.state.accepting = False
            return
        self.book(self.state.manifest["available"][position], "write")

    def book(self, allocation, kind):
        showtime, seat = allocation_pair(allocation, self.state.dataset)
        return self.send_request("POST", "/bookings", kind, 201,
                                 json={"showtime_id": showtime, "seat_ids": [seat]},
                                 headers={"Authorization": "Bearer " + self.token})

    @task
    def request(self):
        if self.state.spec.scenario == "R3":
            wave = self.state.wave
            if wave is None:
                gevent.sleep(.01)
                return
            if wave["started"] is None:
                wave["started"] = perf_counter()
            status = self.book(wave["allocation"], "conflict")
            self.state.finish_wave(wave, status)
            wave["done"].wait()
        elif not self.state.accepting:
            gevent.sleep(.01)
        elif self.state.spec.scenario == "R1":
            self.read_catalog()
        elif self.state.spec.scenario == "R2":
            self.book_unique()
        else:
            self.cycle += 1
            self.book_unique() if self.cycle % 5 == 0 else self.read_catalog()


class BookingComparisonUser(CinemaUser):
    # FastHttpUser configures timeouts on the session, not individual requests.
    connection_timeout = BOOKING_CLIENT_TIMEOUT_SECONDS
    network_timeout = BOOKING_CLIENT_TIMEOUT_SECONDS
    # Apply the same pacing to every arm: fast rejections must not saturate Locust.
    wait_time = constant_pacing(BOOKING_USER_PERIOD_SECONDS)


def execute(spec: RunSpec, manifest: dict, host: str) -> dict:
    state = LoadState(spec, manifest)
    user_class = BookingComparisonUser if spec.variant in BOOKING_VARIANTS else CinemaUser
    environment = Environment(user_classes=[user_class], host=host, stop_timeout=spec.drain)
    environment.phase2 = state
    environment.events.user_error.add_listener(lambda **kwargs: state.errors.append("locust_user_error"))
    runner = environment.create_local_runner()
    try:
        runner.start(spec.users, spawn_rate=max(spec.users, 1))
        runner.spawning_greenlet.join(timeout=30)
        if runner.user_count != spec.users:
            raise RuntimeError("Could not spawn all load users")
        state.gate.set()
        gevent.sleep(spec.warmup)
        state.accepting = False
        deadline = perf_counter() + spec.drain
        while (state.inflight or state.wave is not None) and perf_counter() < deadline:
            gevent.sleep(.01)
        if state.inflight or state.wave is not None:
            raise RuntimeError("Warmup did not drain")
        before = requests.get(host + "/metrics", timeout=5)
        before.raise_for_status()
        started = perf_counter()
        state.ledger = RequestLedger(started, started + spec.duration)
        if spec.scenario == "R3":
            state.wave = state.new_wave()
        state.accepting = True
        environment.stats.reset_all()
        gevent.sleep(spec.duration)
        state.accepting = False
        deadline = perf_counter() + spec.drain
        while (state.inflight or state.wave is not None) and perf_counter() < deadline:
            gevent.sleep(.01)
        if state.inflight or state.wave is not None:
            state.errors.append("drain_incomplete")
        after = requests.get(host + "/metrics", timeout=5)
        after.raise_for_status()
        runner.stop()
        result = state.ledger.summary()
        result.update({"all_statuses": dict(state.all_statuses), "acknowledged_bookings": state.acknowledged,
                       **summarize_waves(state.waves, started, started + spec.duration),
                       "waves": state.waves, "errors": state.errors, "valid": not state.errors,
                       "metrics_before": before.text, "metrics_after": after.text,
                       "measurement_start_monotonic": started, "measurement_end_monotonic": started + spec.duration})
        return result
    finally:
        runner.quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", required=True)
    args = parser.parse_args()
    result = execute(RunSpec(**json.loads(args.spec.read_text())), json.loads(args.manifest.read_text()), args.host)
    write_json(args.output, result)


if __name__ == "__main__":
    main()
