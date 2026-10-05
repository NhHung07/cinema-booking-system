from abc import ABC, abstractmethod

from app.domain.repositories.booking_repository import BookingRepository
from app.domain.repositories.movie_repository import MovieRepository
from app.domain.repositories.seat_repository import SeatRepository
from app.domain.repositories.showtime_repository import ShowtimeRepository
from app.domain.repositories.user_repository import UserRepository


class UnitOfWork(ABC):
    """Ranh giới transaction (Transaction boundary) được yêu cầu bởi các application service.

    Interface này hoàn toàn không phụ thuộc vào web framework hay database implementation cụ thể nào.
    """

    users: UserRepository
    movies: MovieRepository
    showtimes: ShowtimeRepository
    seats: SeatRepository
    bookings: BookingRepository

    @abstractmethod
    def __enter__(self) -> "UnitOfWork": ...

    @abstractmethod
    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None: ...

    @abstractmethod
    def commit(self) -> None: ...

    @abstractmethod
    def rollback(self) -> None: ...
