from locust import HttpUser, between, task


class CinemaVisitor(HttpUser):
    """Read-heavy Phase 1 smoke scenario; IDs assume seeded data exists."""

    wait_time = between(1, 3)

    @task(3)
    def list_movies(self) -> None:
        self.client.get("/movies", name="GET /movies")

    @task(3)
    def list_showtimes(self) -> None:
        self.client.get("/showtimes", name="GET /showtimes")

    @task(1)
    def inspect_seats(self) -> None:
        self.client.get("/showtimes/1/seats", name="GET /showtimes/:id/seats")
