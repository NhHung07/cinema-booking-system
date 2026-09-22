from __future__ import annotations

from locust import task

from benchmark.scenarios.base import DatasetHttpUser, showtime_for_slot


class BookingJourneyUser(DatasetHttpUser):
    """Workload B: login thật, browse catalogue, xem ghế rồi booking."""

    weight = 1

    def on_start(self) -> None:
        super().on_start()
        self.token = self.login()
        self.slot = self.dataset["booking_slots"][self.user_index]
        self.showtime = showtime_for_slot(self.dataset, self.slot)
        self.booking_id: int | None = None

    @task
    def booking_journey(self) -> None:
        self.client.get("/movies", name="GET /movies [booking flow]")
        self.client.get(
            "/showtimes",
            params={"movie_id": self.showtime["movie_id"]},
            name="GET /showtimes?movie_id [booking flow]",
        )
        self.client.get(
            f"/showtimes/{self.slot['showtime_id']}/seats",
            name="GET /showtimes/:id/seats [booking flow]",
        )

        if self.booking_id is None and self.token:
            with self.client.post(
                "/bookings",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "showtime_id": self.slot["showtime_id"],
                    "seat_ids": [self.slot["seat_id"]],
                },
                name="POST /bookings [unique seat]",
                catch_response=True,
            ) as response:
                if response.status_code == 201:
                    self.booking_id = int(response.json()["id"])
                else:
                    response.failure(f"booking returned HTTP {response.status_code}")
        elif self.token:
            self.client.get(
                "/bookings/me",
                headers={"Authorization": f"Bearer {self.token}"},
                name="GET /bookings/me [after booking]",
            )
