from __future__ import annotations

from locust import task

from benchmark.scenarios.base import DatasetHttpUser


class CatalogueUser(DatasetHttpUser):
    """Workload A: 50% movies, 30% showtimes, 20% seat availability."""

    weight = 1

    @task(5)
    def list_movies(self) -> None:
        self.client.get("/movies", name="GET /movies")

    @task(3)
    def list_showtimes(self) -> None:
        self.client.get(
            "/showtimes",
            params={"movie_id": self.random_movie_id()},
            name="GET /showtimes?movie_id",
        )

    @task(2)
    def list_seats(self) -> None:
        showtime = self.random_showtime()
        self.client.get(
            f"/showtimes/{showtime['id']}/seats",
            name="GET /showtimes/:id/seats",
        )
