from types import TracebackType

from sqlalchemy.orm import Session

from app.domain.repositories.unit_of_work import UnitOfWork
from app.infrastructure.repositories.sqlalchemy_booking_repository import SQLAlchemyBookingRepository
from app.infrastructure.repositories.sqlalchemy_movie_repository import SQLAlchemyMovieRepository
from app.infrastructure.repositories.sqlalchemy_seat_repository import SQLAlchemySeatRepository
from app.infrastructure.repositories.sqlalchemy_showtime_repository import SQLAlchemyShowtimeRepository
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: Session) -> None:
        self._session = session
        self.users = SQLAlchemyUserRepository(session)
        self.movies = SQLAlchemyMovieRepository(session)
        self.showtimes = SQLAlchemyShowtimeRepository(session)
        self.seats = SQLAlchemySeatRepository(session)
        self.bookings = SQLAlchemyBookingRepository(session)

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
