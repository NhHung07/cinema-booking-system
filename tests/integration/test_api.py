from fastapi.testclient import TestClient


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


def test_register_duplicate_email_returns_conflict(client: TestClient) -> None:
    _register_and_login(client, "dup@example.com")

    response = client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": "password123", "full_name": "Another Name"},
    )

    assert response.status_code == 409


def test_login_with_wrong_password_returns_unauthorized(client: TestClient) -> None:
    _register_and_login(client, "wrongpass@example.com")

    response = client.post("/auth/login", json={"email": "wrongpass@example.com", "password": "not-the-password"})

    assert response.status_code == 401


def test_protected_endpoint_rejects_malformed_or_missing_token(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"}).status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "NotBearer xyz"}).status_code == 401


def test_get_me_returns_the_authenticated_user(client: TestClient) -> None:
    headers = _register_and_login(client, "me@example.com")

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


def test_user_cannot_access_another_users_booking(client: TestClient, catalog: dict[str, int]) -> None:
    owner_headers = _register_and_login(client, "owner@example.com")
    other_headers = _register_and_login(client, "other@example.com")
    created = client.post(
        "/bookings",
        json={"showtime_id": catalog["showtime_id"], "seat_ids": [catalog["seat_1"]]},
        headers=owner_headers,
    )
    assert created.status_code == 201, created.text
    booking_id = created.json()["id"]

    read_by_other = client.get(f"/bookings/{booking_id}", headers=other_headers)
    cancel_by_other = client.delete(f"/bookings/{booking_id}", headers=other_headers)

    assert read_by_other.status_code == 403
    assert cancel_by_other.status_code == 403


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
