from __future__ import annotations

import itertools
import os
import random
from typing import Any

from locust import HttpUser, between

from benchmark.config import BenchmarkConfig
from benchmark.dataset import benchmark_password, read_dataset


_USER_SEQUENCE = itertools.count()


class DatasetHttpUser(HttpUser):
    abstract = True
    wait_time = between(0.25, 0.75)

    dataset: dict[str, Any]
    user_index: int
    benchmark_user: dict[str, Any]
    rng: random.Random

    def on_start(self) -> None:
        config = BenchmarkConfig.from_env()
        self.dataset = read_dataset(config.dataset_file)
        self.user_index = next(_USER_SEQUENCE)
        users = self.dataset["users"]
        if self.user_index >= len(users):
            raise RuntimeError(
                f"Dataset chỉ có {len(users)} users nhưng workload cần user index {self.user_index}."
            )
        self.benchmark_user = users[self.user_index]
        self.rng = random.Random(config.random_seed + self.user_index)

    def login(self) -> str:
        with self.client.post(
            "/auth/login",
            json={"email": self.benchmark_user["email"], "password": benchmark_password()},
            name="POST /auth/login",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"login returned HTTP {response.status_code}")
                return ""
            token = response.json().get("access_token")
            if not token:
                response.failure("login response does not contain access_token")
                return ""
            return str(token)

    def random_movie_id(self) -> int:
        return int(self.rng.choice(self.dataset["movie_ids"]))

    def random_showtime(self) -> dict[str, Any]:
        return self.rng.choice(self.dataset["showtimes"])


def showtime_for_slot(dataset: dict[str, Any], slot: dict[str, int]) -> dict[str, Any]:
    for showtime in dataset["showtimes"]:
        if int(showtime["id"]) == int(slot["showtime_id"]):
            return showtime
    raise ValueError(f"Không tìm thấy showtime cho slot {slot}")
