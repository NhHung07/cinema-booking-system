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


def test_admin_create_movie_permissions(client: TestClient, session_factory) -> None:
    movie_payload = {
        "title": "Gladiator II",
        "description": "Epic historical action film",
        "duration_minutes": 148,
        "release_date": "2024-11-22",
    }
    # 1. Unauthenticated -> 401
    unauth = client.post("/movies", json=movie_payload)
    assert unauth.status_code == 401

    # 2. Regular user -> 403
    user_headers = _register_and_login(client, "regular_user@example.com")
    forbidden = client.post("/movies", json=movie_payload, headers=user_headers)
    assert forbidden.status_code == 403

    # 3. Admin user -> 201
    from app.core.security import hash_password
    from app.infrastructure.database.models import UserModel

    with session_factory() as session:
        admin_model = UserModel(
            email="admin@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Admin User",
            role="admin",
        )
        session.add(admin_model)
        session.commit()

    login_resp = client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass123"})
    assert login_resp.status_code == 200
    assert login_resp.json()["role"] == "admin"
    admin_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    me_resp = client.get("/auth/me", headers=admin_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "admin"

    created = client.post("/movies", json=movie_payload, headers=admin_headers)
    assert created.status_code == 201, created.text
    created_data = created.json()
    assert created_data["title"] == "Gladiator II"
    assert created_data["duration_minutes"] == 148

    all_movies = client.get("/movies")
    assert any(m["id"] == created_data["id"] for m in all_movies.json())


def test_admin_cannot_book_tickets(client: TestClient, catalog: dict[str, int], session_factory) -> None:
    from app.core.security import hash_password
    from app.infrastructure.database.models import UserModel

    with session_factory() as session:
        admin = UserModel(
            email="admin_booking@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Admin Booking Test",
            role="admin",
        )
        session.add(admin)
        session.commit()

    login_resp = client.post(
        "/auth/login",
        json={"email": "admin_booking@example.com", "password": "adminpass123"},
    )
    assert login_resp.status_code == 200
    admin_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # Admin attempts to book a seat -> 403 Forbidden
    booking_resp = client.post(
        "/bookings",
        json={"showtime_id": catalog["showtime_id"], "seat_ids": [catalog["seat_1"]]},
        headers=admin_headers,
    )
    assert booking_resp.status_code == 403
    assert "quản trị viên" in booking_resp.json()["detail"].lower() or "admin" in booking_resp.json()["detail"].lower()


def test_admin_image_upload_and_movie_creation(client: TestClient, session_factory) -> None:
    import base64
    from app.core.security import hash_password
    from app.infrastructure.database.models import UserModel

    with session_factory() as session:
        admin = UserModel(
            email="admin_upload@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Admin Upload",
            role="admin",
        )
        session.add(admin)
        session.commit()

    login_resp = client.post(
        "/auth/login",
        json={"email": "admin_upload@example.com", "password": "adminpass123"},
    )
    admin_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # 1. Test image upload
    fake_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
    b64_str = f"data:image/png;base64,{base64.b64encode(fake_png_bytes).decode()}"
    upload_resp = client.post(
        "/movies/upload-image",
        json={"filename": "poster.png", "image_data": b64_str},
        headers=admin_headers,
    )
    assert upload_resp.status_code == 200
    image_url = upload_resp.json()["image_url"]
    assert image_url.startswith("/static/uploads/")

    # 2. Test movie creation with poster_url
    movie_payload = {
        "title": "Moana 2",
        "description": "Animated adventure",
        "duration_minutes": 100,
        "release_date": "2024-11-27",
        "poster_url": image_url,
    }
    create_resp = client.post("/movies", json=movie_payload, headers=admin_headers)
    assert create_resp.status_code == 201
    assert create_resp.json()["poster_url"] == image_url


def test_admin_create_showtime(client: TestClient, catalog: dict[str, int], session_factory) -> None:
    from app.core.security import hash_password
    from app.infrastructure.database.models import UserModel

    with session_factory() as session:
        admin = UserModel(
            email="admin_showtime@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Admin Showtime",
            role="admin",
        )
        session.add(admin)
        session.commit()

    login_resp = client.post(
        "/auth/login",
        json={"email": "admin_showtime@example.com", "password": "adminpass123"},
    )
    admin_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    user_headers = _register_and_login(client, "regular_showtime@example.com")

    showtime_payload = {
        "movie_id": catalog["movie_id"],
        "room_name": "ROOM_1",
        "start_time": "2026-11-01T14:00:00Z",
    }

    # 1. Non-admin cannot create showtime
    forbidden = client.post("/showtimes", json=showtime_payload, headers=user_headers)
    assert forbidden.status_code == 403

    # 2. Admin can create showtime
    created = client.post("/showtimes", json=showtime_payload, headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["room_name"] == "ROOM_1"
    assert created.json()["movie_id"] == catalog["movie_id"]


def test_admin_update_and_delete_movie(client: TestClient, session_factory) -> None:
    from app.core.security import hash_password
    from app.infrastructure.database.models import UserModel

    with session_factory() as session:
        admin = UserModel(
            email="admin_crud_movie@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Admin Movie CRUD",
            role="admin",
        )
        session.add(admin)
        session.commit()

    login_resp = client.post(
        "/auth/login",
        json={"email": "admin_crud_movie@example.com", "password": "adminpass123"},
    )
    admin_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # 1. Create a movie
    create_resp = client.post(
        "/movies",
        json={
            "title": "Old Movie Title",
            "description": "Old description",
            "duration_minutes": 100,
            "release_date": "2026-01-01",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    movie_id = create_resp.json()["id"]

    # 2. Update movie
    update_resp = client.put(
        f"/movies/{movie_id}",
        json={
            "title": "New Movie Title",
            "description": "New updated description",
            "duration_minutes": 135,
            "release_date": "2026-05-20",
            "poster_url": "https://example.com/poster.jpg",
        },
        headers=admin_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["title"] == "New Movie Title"
    assert update_resp.json()["duration_minutes"] == 135
    assert update_resp.json()["poster_url"] == "https://example.com/poster.jpg"

    # 3. Non-admin cannot delete
    user_headers = _register_and_login(client, "regular_delete@example.com")
    forbidden = client.delete(f"/movies/{movie_id}", headers=user_headers)
    assert forbidden.status_code == 403

    # 4. Admin deletes movie
    del_resp = client.delete(f"/movies/{movie_id}", headers=admin_headers)
    assert del_resp.status_code == 200
    assert client.get(f"/movies/{movie_id}").status_code == 404


def test_admin_update_and_delete_showtime(client: TestClient, catalog: dict[str, int], session_factory) -> None:
    from app.core.security import hash_password
    from app.infrastructure.database.models import UserModel

    with session_factory() as session:
        admin = UserModel(
            email="admin_crud_st@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Admin Showtime CRUD",
            role="admin",
        )
        session.add(admin)
        session.commit()

    login_resp = client.post(
        "/auth/login",
        json={"email": "admin_crud_st@example.com", "password": "adminpass123"},
    )
    admin_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # 1. Create a showtime
    create_resp = client.post(
        "/showtimes",
        json={
            "movie_id": catalog["movie_id"],
            "room_name": "ROOM_1",
            "start_time": "2026-12-01T10:00:00Z",
        },
        headers=admin_headers,
    )
    assert create_resp.status_code == 201
    st_id = create_resp.json()["id"]

    # 2. Get single showtime
    get_resp = client.get(f"/showtimes/{st_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == st_id
    assert get_resp.json()["room_name"] == "ROOM_1"

    # 3. Update showtime
    update_resp = client.put(
        f"/showtimes/{st_id}",
        json={
            "room_name": "ROOM_2",
            "start_time": "2026-12-01T15:30:00Z",
        },
        headers=admin_headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["room_name"] == "ROOM_2"

    # 4. Delete showtime
    del_resp = client.delete(f"/showtimes/{st_id}", headers=admin_headers)
    assert del_resp.status_code == 200
    assert client.get(f"/showtimes/{st_id}").status_code == 404

