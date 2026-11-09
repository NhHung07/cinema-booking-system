from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import random

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.infrastructure.database.models import BookingModel, BookingSeatModel, MovieModel, SeatModel, ShowtimeModel, UserModel
from experiments.phase2.config import SEED


@dataclass(frozen=True)
class DatasetSpec:
    users: int = 2000
    movies: int = 250
    rooms: int = 50
    seats_per_room: int = 200
    showtimes: int = 5000
    bookings: int = 100000

    def __post_init__(self):
        if min(self.users, self.movies, self.rooms, self.seats_per_room, self.showtimes) < 1:
            raise ValueError("Dataset dimensions must be positive")
        if not 0 <= self.bookings < self.showtimes * self.seats_per_room:
            raise ValueError("Background bookings must leave available seats")


def build_manifest(spec: DatasetSpec) -> dict:
    allocations = list(range(spec.showtimes * spec.seats_per_room))
    random.Random(SEED).shuffle(allocations)
    manifest = {"spec": asdict(spec), "seed": SEED,
                "background": allocations[:spec.bookings], "available": allocations[spec.bookings:]}
    manifest["sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    return manifest


def allocation_pair(allocation: int, spec: DatasetSpec) -> tuple[int, int]:
    show_index, local_seat = divmod(allocation, spec.seats_per_room)
    if not 0 <= show_index < spec.showtimes:
        raise ValueError("Allocation outside dataset")
    return show_index + 1, (show_index % spec.rooms) * spec.seats_per_room + local_seat + 1


def _bulk(session: Session, model, rows) -> None:
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == 2000:
            session.execute(insert(model), batch)
            batch = []
    if batch:
        session.execute(insert(model), batch)


def seed_database(engine, manifest: dict) -> None:
    spec = DatasetSpec(**manifest["spec"])
    start = datetime(2030, 1, 1, tzinfo=UTC)
    password_hash = hash_password("phase2-fixture-only")
    with Session(engine) as session:
        _bulk(session, UserModel, ({"id": i + 1, "email": f"user{i+1}@phase2.invalid", "full_name": f"User {i+1}",
                                  "password_hash": password_hash, "created_at": start} for i in range(spec.users)))
        _bulk(session, MovieModel, ({"id": i + 1, "title": f"Movie {i+1}", "description": "Mô tả phim. " * 80,
                                   "duration_minutes": 120, "release_date": start.date(), "created_at": start}
                                  for i in range(spec.movies)))
        _bulk(session, SeatModel, ({"id": room * spec.seats_per_room + seat + 1, "room_name": f"ROOM_{room+1}",
                                  "row": f"R{seat // 10 + 1:02}", "number": seat % 10 + 1}
                                 for room in range(spec.rooms) for seat in range(spec.seats_per_room)))
        _bulk(session, ShowtimeModel, ({"id": i + 1, "movie_id": i % spec.movies + 1,
                                      "room_name": f"ROOM_{i % spec.rooms+1}",
                                      "start_time": start + timedelta(hours=(i // spec.rooms) * 3), "created_at": start}
                                     for i in range(spec.showtimes)))
        _bulk(session, BookingModel, ({"id": i + 1, "user_id": i % spec.users + 1,
                                     "showtime_id": allocation_pair(a, spec)[0], "status": "CONFIRMED", "created_at": start}
                                    for i, a in enumerate(manifest["background"])))
        _bulk(session, BookingSeatModel, ({"id": i + 1, "booking_id": i + 1,
                                         "showtime_id": allocation_pair(a, spec)[0], "seat_id": allocation_pair(a, spec)[1]}
                                        for i, a in enumerate(manifest["background"])))
        for table in ["users", "movies", "seats", "showtimes", "bookings", "booking_seats"]:
            session.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT max(id) FROM {table}))"))
        session.commit()
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("ANALYZE"))


def database_fingerprint(engine) -> dict:
    # Aggregate every row, including payloads, to detect an incorrect template restore.
    result = {}
    with engine.connect() as conn:
        for table in ["users", "movies", "seats", "showtimes", "bookings", "booking_seats"]:
            result[table] = list(conn.execute(text(
                f"SELECT count(*), coalesce(sum(('x' || substr(md5(row_to_json(t)::text), 1, 15))::bit(60)::bigint),0)::text FROM {table} t"
            )).one())
    return result


def verify_bookings(engine, background: int) -> dict:
    with engine.connect() as conn:
        counts = conn.execute(text("SELECT (SELECT count(*) FROM bookings), (SELECT count(*) FROM booking_seats)")).one()
        orphan = conn.scalar(text("SELECT count(*) FROM bookings b WHERE b.status='CONFIRMED' AND NOT EXISTS (SELECT 1 FROM booking_seats s WHERE s.booking_id=b.id)"))
        duplicates = conn.scalar(text("SELECT count(*) FROM (SELECT showtime_id,seat_id FROM booking_seats GROUP BY showtime_id,seat_id HAVING count(*)>1) x"))
    return {"bookings": counts[0], "allocations": counts[1], "new_bookings": counts[0] - background,
            "orphans": orphan, "duplicates": duplicates,
            "valid": orphan == 0 and duplicates == 0 and counts[0] == counts[1] and counts[0] >= background}
