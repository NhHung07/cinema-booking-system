from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, or_, select
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

BENCHMARK_EMAIL_PATTERN = "bench-user-%@example.com"
BENCHMARK_MOVIE_PATTERN = "BENCH_MOVIE_%"
BENCHMARK_ROOM_PATTERN = "BENCH_ROOM_%"
DEFAULT_BENCHMARK_PASSWORD = "benchmark-password-123"


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    user_count: int = 220
    movie_count: int = 12
    showtimes_per_movie: int = 3
    room_count: int = 3
    seat_rows: str = "ABCD"
    seats_per_row: int = 5
    random_seed: int = 42

    @property
    def seat_count(self) -> int:
        return self.room_count * len(self.seat_rows) * self.seats_per_row

    @property
    def showtime_count(self) -> int:
        return self.movie_count * self.showtimes_per_movie


def benchmark_password() -> str:
    return os.getenv("BENCH_USER_PASSWORD", DEFAULT_BENCHMARK_PASSWORD)


def reset_benchmark_data(session: Session) -> dict[str, int]:
    """Chỉ xóa dataset có namespace BENCH_, không đụng dữ liệu ứng dụng khác."""
    user_ids = list(
        session.scalars(select(UserModel.id).where(UserModel.email.like(BENCHMARK_EMAIL_PATTERN))).all()
    )
    movie_ids = list(
        session.scalars(select(MovieModel.id).where(MovieModel.title.like(BENCHMARK_MOVIE_PATTERN))).all()
    )
    showtime_ids = list(
        session.scalars(
            select(ShowtimeModel.id).where(
                or_(
                    ShowtimeModel.movie_id.in_(movie_ids) if movie_ids else False,
                    ShowtimeModel.room_name.like(BENCHMARK_ROOM_PATTERN),
                )
            )
        ).all()
    )
    booking_ids = list(
        session.scalars(
            select(BookingModel.id).where(
                or_(
                    BookingModel.user_id.in_(user_ids) if user_ids else False,
                    BookingModel.showtime_id.in_(showtime_ids) if showtime_ids else False,
                )
            )
        ).all()
    )

    if booking_ids or showtime_ids:
        session.execute(
            delete(BookingSeatModel).where(
                or_(
                    BookingSeatModel.booking_id.in_(booking_ids) if booking_ids else False,
                    BookingSeatModel.showtime_id.in_(showtime_ids) if showtime_ids else False,
                )
            )
        )
    if booking_ids:
        session.execute(delete(BookingModel).where(BookingModel.id.in_(booking_ids)))
    if showtime_ids:
        session.execute(delete(ShowtimeModel).where(ShowtimeModel.id.in_(showtime_ids)))
    session.execute(delete(SeatModel).where(SeatModel.room_name.like(BENCHMARK_ROOM_PATTERN)))
    if movie_ids:
        session.execute(delete(MovieModel).where(MovieModel.id.in_(movie_ids)))
    if user_ids:
        session.execute(delete(UserModel).where(UserModel.id.in_(user_ids)))
    session.commit()
    return {
        "users": len(user_ids),
        "movies": len(movie_ids),
        "showtimes": len(showtime_ids),
        "bookings": len(booking_ids),
    }


def seed_benchmark_data(session: Session, spec: DatasetSpec | None = None) -> dict[str, Any]:
    selected_spec = spec or DatasetSpec()
    slots_per_showtime = len(selected_spec.seat_rows) * selected_spec.seats_per_row
    if selected_spec.user_count > selected_spec.showtime_count * slots_per_showtime:
        raise ValueError("Dataset does not contain enough unique booking slots for all benchmark users")

    reset_benchmark_data(session)
    shared_hash = hash_password(benchmark_password())
    users = [
        UserModel(
            email=f"bench-user-{index:03d}@example.com",
            password_hash=shared_hash,
            full_name=f"Benchmark User {index:03d}",
        )
        for index in range(1, selected_spec.user_count + 1)
    ]
    session.add_all(users)

    movies = [
        MovieModel(
            title=f"BENCH_MOVIE_{index:02d}",
            description=f"Deterministic Phase 1 benchmark movie {index:02d}.",
            duration_minutes=90 + index * 5,
            release_date=date(2010 + index, ((index - 1) % 12) + 1, min(index, 28)),
        )
        for index in range(1, selected_spec.movie_count + 1)
    ]
    session.add_all(movies)

    seats: list[SeatModel] = []
    for room_index in range(1, selected_spec.room_count + 1):
        room_name = f"BENCH_ROOM_{room_index}"
        seats.extend(
            SeatModel(room_name=room_name, row=row, number=number)
            for row in selected_spec.seat_rows
            for number in range(1, selected_spec.seats_per_row + 1)
        )
    session.add_all(seats)
    session.flush()

    fixed_start = datetime(2030, 1, 1, 8, 0, tzinfo=UTC)
    showtimes: list[ShowtimeModel] = []
    showtime_index = 0
    for movie in movies:
        for _ in range(selected_spec.showtimes_per_movie):
            room_number = (showtime_index % selected_spec.room_count) + 1
            showtimes.append(
                ShowtimeModel(
                    movie_id=movie.id,
                    start_time=fixed_start + timedelta(hours=showtime_index * 2),
                    room_name=f"BENCH_ROOM_{room_number}",
                )
            )
            showtime_index += 1
    session.add_all(showtimes)
    session.commit()

    seats_by_room: dict[str, list[int]] = {}
    for seat in sorted(seats, key=lambda item: (item.room_name, item.row, item.number)):
        seats_by_room.setdefault(seat.room_name, []).append(seat.id)

    showtime_records = [
        {
            "id": showtime.id,
            "movie_id": showtime.movie_id,
            "room_name": showtime.room_name,
            "seat_ids": seats_by_room[showtime.room_name],
        }
        for showtime in showtimes
    ]
    all_slots = [
        {"showtime_id": showtime["id"], "seat_id": seat_id}
        for showtime in showtime_records
        for seat_id in showtime["seat_ids"]
    ]
    metadata: dict[str, Any] = {
        "random_seed": selected_spec.random_seed,
        "counts": {
            "users": len(users),
            "movies": len(movies),
            "showtimes": len(showtimes),
            "rooms": selected_spec.room_count,
            "seats": len(seats),
            "booking_slots": len(all_slots),
        },
        "users": [{"id": user.id, "email": user.email} for user in users],
        "movie_ids": [movie.id for movie in movies],
        "showtimes": showtime_records,
        "booking_slots": all_slots[: selected_spec.user_count],
        "concurrent_target": all_slots[-1],
    }
    validate_dataset(metadata)
    return metadata


def validate_dataset(metadata: dict[str, Any]) -> None:
    users = metadata.get("users")
    movie_ids = set(metadata.get("movie_ids", []))
    showtimes = metadata.get("showtimes")
    slots = metadata.get("booking_slots")
    target = metadata.get("concurrent_target")
    if not users or not movie_ids or not showtimes or not slots or not target:
        raise ValueError("Benchmark dataset metadata is incomplete")

    showtime_map = {item["id"]: item for item in showtimes}
    if len(showtime_map) != len(showtimes):
        raise ValueError("Benchmark showtime IDs must be unique")
    if any(item["movie_id"] not in movie_ids for item in showtimes):
        raise ValueError("Benchmark showtime references a missing movie")

    for slot in [*slots, target]:
        showtime = showtime_map.get(slot.get("showtime_id"))
        if showtime is None:
            raise ValueError("Benchmark slot references a missing showtime")
        if slot.get("seat_id") not in showtime.get("seat_ids", []):
            raise ValueError("Benchmark slot references a seat outside the showtime room")


def write_dataset(metadata: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def read_dataset(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Benchmark dataset file not found: {path}. Run seed_benchmark.py first.")
    metadata = json.loads(path.read_text(encoding="utf-8"))
    validate_dataset(metadata)
    return metadata


def concurrent_allocation_count(session: Session, metadata: dict[str, Any]) -> int:
    target = metadata["concurrent_target"]
    return int(
        session.scalar(
            select(func.count(BookingSeatModel.id)).where(
                BookingSeatModel.showtime_id == target["showtime_id"],
                BookingSeatModel.seat_id == target["seat_id"],
            )
        )
        or 0
    )
