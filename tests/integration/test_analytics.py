from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.infrastructure.database.models import (
    BookingModel,
    BookingSeatModel,
    MovieModel,
    SeatModel,
    ShowtimeModel,
    UserModel,
)


def _setup_analytics_test_data(session_factory: Callable[[], Session]) -> dict[str, int]:
    with session_factory() as session:
        # Create admin
        admin = UserModel(
            email="admin_analytics@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Admin Analytics",
            role="admin",
        )
        # Create regular user
        user = UserModel(
            email="user_analytics@example.com",
            password_hash=hash_password("userpass123"),
            full_name="User Analytics",
            role="user",
        )
        session.add_all([admin, user])
        session.flush()

        # Create movies
        movie1 = MovieModel(
            title="Dune Part Two",
            description="Epic sci-fi",
            duration_minutes=166,
            release_date=datetime(2024, 3, 1, tzinfo=UTC).date(),
            poster_url="https://example.com/dune.jpg",
        )
        movie2 = MovieModel(
            title="Oppenheimer",
            description="Historical drama",
            duration_minutes=180,
            release_date=datetime(2023, 7, 21, tzinfo=UTC).date(),
            poster_url="https://example.com/oppy.jpg",
        )
        session.add_all([movie1, movie2])
        session.flush()

        # Create seats for ROOM_1: A1 (regular), B2 (VIP)
        seat_a1 = SeatModel(room_name="ROOM_1", row="A", number=1)
        seat_b2 = SeatModel(room_name="ROOM_1", row="B", number=2)
        # Create seat for ROOM_2: A1 (regular)
        seat_r2_a1 = SeatModel(room_name="ROOM_2", row="A", number=1)
        session.add_all([seat_a1, seat_b2, seat_r2_a1])
        session.flush()

        # Create showtimes
        now = datetime.now(UTC)
        st1 = ShowtimeModel(movie_id=movie1.id, room_name="ROOM_1", start_time=now + timedelta(hours=2))
        st2 = ShowtimeModel(movie_id=movie2.id, room_name="ROOM_2", start_time=now + timedelta(hours=4))
        session.add_all([st1, st2])
        session.flush()

        # Booking 1: Confirmed with A1 (90k) and B2 (110k) => total 200k, 2 tickets
        b1 = BookingModel(user_id=user.id, showtime_id=st1.id, status="CONFIRMED", created_at=now)
        session.add(b1)
        session.flush()
        bs1 = BookingSeatModel(booking_id=b1.id, showtime_id=st1.id, seat_id=seat_a1.id)
        bs2 = BookingSeatModel(booking_id=b1.id, showtime_id=st1.id, seat_id=seat_b2.id)
        session.add_all([bs1, bs2])

        # Booking 2: Cancelled booking (should NOT count in revenue/tickets)
        b2 = BookingModel(user_id=user.id, showtime_id=st2.id, status="CANCELLED", created_at=now)
        session.add(b2)
        session.flush()

        session.commit()

        return {
            "admin_id": admin.id,
            "user_id": user.id,
            "movie1_id": movie1.id,
            "movie2_id": movie2.id,
            "b1_id": b1.id,
            "b2_id": b2.id,
        }


def test_analytics_permissions(client: TestClient, session_factory: Callable[[], Session]) -> None:
    _setup_analytics_test_data(session_factory)

    # 1. Unauthenticated -> 401
    resp = client.get("/admin/analytics/overview")
    assert resp.status_code == 401

    # 2. Regular user -> 403
    user_login = client.post("/auth/login", json={"email": "user_analytics@example.com", "password": "userpass123"})
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]
    user_resp = client.get("/admin/analytics/overview", headers={"Authorization": f"Bearer {user_token}"})
    assert user_resp.status_code == 403

    # 3. Admin user -> 200
    admin_login = client.post("/auth/login", json={"email": "admin_analytics@example.com", "password": "adminpass123"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]
    admin_resp = client.get("/admin/analytics/overview", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_resp.status_code == 200


def test_analytics_metrics_calculation(client: TestClient, session_factory: Callable[[], Session]) -> None:
    data = _setup_analytics_test_data(session_factory)

    admin_login = client.post("/auth/login", json={"email": "admin_analytics@example.com", "password": "adminpass123"})
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/admin/analytics/overview?days=7", headers=headers)
    assert resp.status_code == 200
    body = resp.json()

    summary = body["summary"]
    # Total revenue: A1 (regular: 90,000) + B2 (VIP: 110,000) = 200,000
    assert summary["total_revenue"] == 200000
    # Total tickets: 2 tickets in confirmed booking
    assert summary["total_tickets"] == 2
    # Total confirmed bookings: 1 (cancelled booking b2 is ignored)
    assert summary["total_bookings"] == 1
    # Total customers: 1 (user_analytics, role="user")
    assert summary["total_customers"] >= 1
    # Average occupancy rate > 0
    assert summary["average_occupancy_rate"] > 0

    # Check revenue timeline
    timeline = body["revenue_timeline"]
    assert len(timeline) == 7
    total_timeline_rev = sum(pt["revenue"] for pt in timeline)
    total_timeline_tickets = sum(pt["tickets"] for pt in timeline)
    assert total_timeline_rev == 200000
    assert total_timeline_tickets == 2

    # Check top movies
    top_movies = body["top_movies"]
    assert len(top_movies) == 1
    assert top_movies[0]["movie_id"] == data["movie1_id"]
    assert top_movies[0]["title"] == "Dune Part Two"
    assert top_movies[0]["tickets_sold"] == 2
    assert top_movies[0]["total_revenue"] == 200000

    # Check room occupancy
    room_stats = body["room_occupancy"]
    assert len(room_stats) >= 2
    room1 = next((r for r in room_stats if r["room_name"] == "ROOM_1"), None)
    assert room1 is not None
    assert room1["booked_seats"] == 2
    assert room1["occupancy_rate"] > 0

    # Check recent bookings
    recent = body["recent_bookings"]
    assert len(recent) >= 2
    assert recent[0]["booking_id"] in (data["b1_id"], data["b2_id"])
    confirmed_b = next((b for b in recent if b["booking_id"] == data["b1_id"]), None)
    assert confirmed_b is not None
    assert confirmed_b["status"] == "CONFIRMED"
    assert set(confirmed_b["seat_labels"]) == {"A1", "B2"}
    assert confirmed_b["total_amount"] == 200000


def test_analytics_days_filter(client: TestClient, session_factory: Callable[[], Session]) -> None:
    _setup_analytics_test_data(session_factory)

    admin_login = client.post("/auth/login", json={"email": "admin_analytics@example.com", "password": "adminpass123"})
    admin_token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    # days=30
    resp_30 = client.get("/admin/analytics/overview?days=30", headers=headers)
    assert resp_30.status_code == 200
    assert len(resp_30.json()["revenue_timeline"]) == 30

    # days=0 (all time)
    resp_all = client.get("/admin/analytics/overview?days=0", headers=headers)
    assert resp_all.status_code == 200
    assert resp_all.json()["summary"]["total_revenue"] == 200000

