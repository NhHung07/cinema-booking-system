from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.config import Settings
from app.core.security import create_access_token
from app.main import create_app


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_login_and_catalog(client: TestClient, catalog: dict[str, int]) -> None:
    headers = _register_and_login(client, "first@example.com")

    movies = client.get("/movies")
    assert movies.status_code == 200
    assert movies.json()[0]["id"] == catalog["movie_id"]

    showtimes = client.get("/showtimes", params={"movie_id": catalog["movie_id"]})
    assert showtimes.status_code == 200
    assert showtimes.json()[0]["id"] == catalog["showtime_id"]

    assert client.post("/bookings", json={"showtime_id": catalog["showtime_id"], "seat_ids": [catalog["seat_1"]]}).status_code == 401
    assert headers["Authorization"].startswith("Bearer ")


def test_booking_conflict_and_cancellation_releases_seat(client: TestClient, catalog: dict[str, int]) -> None:
    first_headers = _register_and_login(client, "first@example.com")
    second_headers = _register_and_login(client, "second@example.com")
    request_body = {"showtime_id": catalog["showtime_id"], "seat_ids": [catalog["seat_1"], catalog["seat_2"]]}

    created = client.post("/bookings", json=request_body, headers=first_headers)
    assert created.status_code == 201, created.text
    booking_id = created.json()["id"]

    conflict = client.post("/bookings", json=request_body, headers=second_headers)
    assert conflict.status_code == 409

    seats = client.get(f"/showtimes/{catalog['showtime_id']}/seats")
    assert seats.status_code == 200
    assert {seat["available"] for seat in seats.json()["seats"][:2]} == {False}

    mine = client.get("/bookings/me", headers=first_headers)
    assert mine.status_code == 200
    assert mine.json()[0]["id"] == booking_id

    cancelled = client.delete(f"/bookings/{booking_id}", headers=first_headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    replacement = client.post("/bookings", json=request_body, headers=second_headers)
    assert replacement.status_code == 201, replacement.text


def test_cors_allows_the_vite_development_origin(client: TestClient) -> None:
    response = client.options(
        "/bookings",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_split_booking_auth_returns_connection_before_booking(session_factory, catalog):
    settings = Settings(jwt_secret_key="test-secret-key-with-at-least-thirty-two-bytes",
                        booking_split_auth=True)
    pool = session_factory.kw["bind"].pool
    calls = []
    event.listen(pool, "checkout", lambda *args: calls.append("checkout"))
    event.listen(pool, "checkin", lambda *args: calls.append("checkin"))
    with TestClient(create_app(settings=settings, session_factory=session_factory)) as client:
        headers = _register_and_login(client, "split@example.com")
        payload = {"showtime_id": catalog["showtime_id"], "seat_ids": [catalog["seat_1"]]}
        calls.clear()
        assert client.post("/bookings", json=payload).status_code == 401
        assert calls == []
        absent = {"Authorization": "Bearer " + create_access_token(999, settings)}
        assert client.post("/bookings", json=payload, headers=absent).status_code == 401
        assert calls == ["checkout", "checkin"]
        calls.clear()
        created = client.post("/bookings", json=payload, headers=headers)
        assert created.status_code == 201
        assert calls == ["checkout", "checkin", "checkout", "checkin"]
        assert client.post("/bookings", json=payload, headers=headers).status_code == 409
        assert client.delete(f"/bookings/{created.json()['id']}", headers=headers).status_code == 200
