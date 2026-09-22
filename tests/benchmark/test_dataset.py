from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    BookingModel,
    BookingSeatModel,
    MovieModel,
    UserModel,
)
from benchmark.dataset import DatasetSpec, reset_benchmark_data, seed_benchmark_data, validate_dataset


def valid_metadata() -> dict[str, object]:
    return {
        "users": [{"id": 1, "email": "bench-user-001@example.com"}],
        "movie_ids": [10],
        "showtimes": [{"id": 20, "movie_id": 10, "room_name": "BENCH_ROOM_1", "seat_ids": [30]}],
        "booking_slots": [{"showtime_id": 20, "seat_id": 30}],
        "concurrent_target": {"showtime_id": 20, "seat_id": 30},
    }


def test_dataset_selector_rejects_unknown_showtime() -> None:
    metadata = valid_metadata()
    metadata["booking_slots"] = [{"showtime_id": 999, "seat_id": 30}]
    with pytest.raises(ValueError, match="missing showtime"):
        validate_dataset(metadata)


def test_dataset_selector_rejects_seat_outside_room() -> None:
    metadata = valid_metadata()
    metadata["concurrent_target"] = {"showtime_id": 20, "seat_id": 999}
    with pytest.raises(ValueError, match="outside the showtime room"):
        validate_dataset(metadata)


def test_reset_only_removes_namespaced_benchmark_data() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        preserved = MovieModel(
            title="User Movie",
            description="must remain",
            duration_minutes=100,
            release_date=date(2020, 1, 1),
        )
        session.add(preserved)
        session.commit()
        metadata = seed_benchmark_data(
            session,
            DatasetSpec(
                user_count=2,
                movie_count=2,
                showtimes_per_movie=1,
                room_count=1,
                seat_rows="AB",
                seats_per_row=2,
            ),
        )
        booking = BookingModel(
            user_id=metadata["users"][0]["id"],
            showtime_id=metadata["booking_slots"][0]["showtime_id"],
            status="CONFIRMED",
        )
        session.add(booking)
        session.flush()
        session.add(
            BookingSeatModel(
                booking_id=booking.id,
                showtime_id=metadata["booking_slots"][0]["showtime_id"],
                seat_id=metadata["booking_slots"][0]["seat_id"],
            )
        )
        session.commit()

        removed = reset_benchmark_data(session)

        assert removed == {"users": 2, "movies": 2, "showtimes": 2, "bookings": 1}
        assert session.scalar(select(func.count(UserModel.id))) == 0
        assert session.scalar(select(func.count(BookingModel.id))) == 0
        assert session.scalar(select(func.count(BookingSeatModel.id))) == 0
        assert session.scalars(select(MovieModel.title)).all() == ["User Movie"]
