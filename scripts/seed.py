"""Create small, idempotent demo data after `alembic upgrade head`."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

# Allow the documented `python scripts/seed.py` command to import the app package.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.infrastructure.database.models import MovieModel, SeatModel, ShowtimeModel
from app.infrastructure.database.session import SessionLocal


def main() -> None:
    with SessionLocal() as session:
        interstellar = session.scalar(select(MovieModel).where(MovieModel.title == "Interstellar"))
        if interstellar is None:
            interstellar = MovieModel(
                title="Interstellar",
                description="A team travels through a wormhole to save humanity.",
                duration_minutes=169,
                release_date=datetime(2014, 11, 7, tzinfo=UTC).date(),
            )
            session.add(interstellar)

        inception = session.scalar(select(MovieModel).where(MovieModel.title == "Inception"))
        if inception is None:
            inception = MovieModel(
                title="Inception",
                description="A thief enters dreams to plant an idea.",
                duration_minutes=148,
                release_date=datetime(2010, 7, 16, tzinfo=UTC).date(),
            )
            session.add(inception)
        session.flush()

        if not session.scalar(select(SeatModel.id).where(SeatModel.room_name == "ROOM_1").limit(1)):
            session.add_all(
                [SeatModel(room_name="ROOM_1", row=row, number=number) for row in "ABC" for number in range(1, 6)]
            )

        if not session.scalar(select(ShowtimeModel.id).where(ShowtimeModel.room_name == "ROOM_1").limit(1)):
            starts_at = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
            session.add_all(
                [
                    ShowtimeModel(movie_id=interstellar.id, room_name="ROOM_1", start_time=starts_at),
                    ShowtimeModel(movie_id=inception.id, room_name="ROOM_1", start_time=starts_at + timedelta(hours=3)),
                ]
            )
        session.commit()
    print("Seed data is ready.")


if __name__ == "__main__":
    main()
