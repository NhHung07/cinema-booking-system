from datetime import date

from app.core.exceptions import MovieNotFoundError, ShowtimeNotFoundError
from app.domain.entities import Movie, Seat, Showtime
from app.domain.repositories.unit_of_work import UnitOfWork


class CatalogService:
    """Read-only movie and showtime use cases."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def list_movies(self) -> list[Movie]:
        with self._unit_of_work as uow:
            return uow.movies.list()

    def get_movie(self, movie_id: int) -> Movie:
        with self._unit_of_work as uow:
            movie = uow.movies.get_by_id(movie_id)
            if movie is None:
                raise MovieNotFoundError("Movie was not found")
            return movie

    def list_showtimes(self, movie_id: int | None = None, show_date: date | None = None) -> list[Showtime]:
        with self._unit_of_work as uow:
            return uow.showtimes.list(movie_id=movie_id, show_date=show_date)

    def get_showtime_seats(self, showtime_id: int) -> tuple[Showtime, list[Seat], set[int]]:
        with self._unit_of_work as uow:
            showtime = uow.showtimes.get_by_id(showtime_id)
            if showtime is None:
                raise ShowtimeNotFoundError("Showtime was not found")
            seats = uow.seats.list_by_room(showtime.room_name)
            booked_seat_ids = uow.bookings.booked_seat_ids(showtime_id)
            return showtime, seats, booked_seat_ids
