from collections.abc import Callable, Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import MovieModel, SeatModel, ShowtimeModel
from app.main import create_app


@pytest.fixture
def session_factory() -> Callable[[], Session]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(session_factory: Callable[[], Session]) -> Generator[TestClient, None, None]:
    settings = Settings(
        database_url="sqlite+pysqlite://",
        jwt_secret_key="test-secret-key-with-at-least-thirty-two-bytes",
        access_token_expire_minutes=60,
    )
    with TestClient(create_app(settings=settings, session_factory=session_factory)) as test_client:
        yield test_client


@pytest.fixture
def catalog(session_factory: Callable[[], Session]) -> dict[str, int]:
    with session_factory() as session:
        movie = MovieModel(
            title="Interstellar",
            description="Space drama",
            duration_minutes=169,
            release_date=datetime(2014, 11, 7, tzinfo=UTC).date(),
        )
        session.add(movie)
        session.flush()
        showtime = ShowtimeModel(movie_id=movie.id, room_name="ROOM_1", start_time=datetime.now(UTC))
        seats = [
            SeatModel(room_name="ROOM_1", row="A", number=1),
            SeatModel(room_name="ROOM_1", row="A", number=2),
            SeatModel(room_name="ROOM_2", row="A", number=1),
        ]
        session.add_all([showtime, *seats])
        session.commit()
        return {"movie_id": movie.id, "showtime_id": showtime.id, "seat_1": seats[0].id, "seat_2": seats[1].id}
