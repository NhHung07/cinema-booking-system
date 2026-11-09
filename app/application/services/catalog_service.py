from datetime import date, datetime

from app.application.ports.catalog_cache import CatalogCache
from app.core.exceptions import InvalidBookingError, MovieNotFoundError, ShowtimeNotFoundError
from app.domain.entities import Movie, Seat, Showtime
from app.domain.repositories.unit_of_work import UnitOfWork


class CatalogService:
    """Các use case cho movie và showtime."""

    def __init__(self, unit_of_work: UnitOfWork, cache: CatalogCache | None = None) -> None:
        self._unit_of_work = unit_of_work
        self._cache = cache

    def list_movies(self) -> list[Movie]:
        if self._cache is not None:
            cached = self._cache.get_movies()
            if cached is not None:
                return cached
        with self._unit_of_work as uow:
            movies = uow.movies.list()
        if self._cache is not None:
            self._cache.put_movies(movies)
        return movies

    def get_movie(self, movie_id: int) -> Movie:
        if self._cache is not None:
            cached = self._cache.get_movie(movie_id)
            if cached is not None:
                return cached
        with self._unit_of_work as uow:
            movie = uow.movies.get_by_id(movie_id)
            if movie is None:
                raise MovieNotFoundError("Movie was not found")
        if self._cache is not None:
            self._cache.put_movie(movie)
        return movie

    def create_movie(
        self,
        title: str,
        description: str,
        duration_minutes: int,
        release_date: date,
        poster_url: str | None = None,
    ) -> Movie:
        with self._unit_of_work as uow:
            movie = uow.movies.add(
                Movie(
                    id=None,
                    title=title.strip(),
                    description=description.strip(),
                    duration_minutes=duration_minutes,
                    release_date=release_date,
                    poster_url=poster_url.strip() if poster_url else None,
                )
            )
            uow.commit()
            return movie

    def create_showtime(self, movie_id: int, room_name: str, start_time: datetime) -> Showtime:
        with self._unit_of_work as uow:
            movie = uow.movies.get_by_id(movie_id)
            if movie is None:
                raise MovieNotFoundError("Movie was not found")
            seats = uow.seats.list_by_room(room_name.strip())
            if not seats:
                raise InvalidBookingError(f"Phòng chiếu '{room_name}' không tồn tại trong hệ thống")
            showtime = uow.showtimes.add(
                Showtime(
                    id=None,
                    movie_id=movie_id,
                    room_name=room_name.strip(),
                    start_time=start_time,
                )
            )
            uow.commit()
            return showtime

    def update_movie(
        self,
        movie_id: int,
        title: str,
        description: str,
        duration_minutes: int,
        release_date: date,
        poster_url: str | None = None,
    ) -> Movie:
        with self._unit_of_work as uow:
            movie = uow.movies.get_by_id(movie_id)
            if movie is None:
                raise MovieNotFoundError("Không tìm thấy phim")
            updated = uow.movies.update(
                Movie(
                    id=movie_id,
                    title=title.strip(),
                    description=description.strip(),
                    duration_minutes=duration_minutes,
                    release_date=release_date,
                    poster_url=poster_url.strip() if poster_url else None,
                    created_at=movie.created_at,
                )
            )
            uow.commit()
            return updated

    def delete_movie(self, movie_id: int) -> None:
        with self._unit_of_work as uow:
            movie = uow.movies.get_by_id(movie_id)
            if movie is None:
                raise MovieNotFoundError("Không tìm thấy phim")
            showtimes = uow.showtimes.list(movie_id=movie_id)
            for st in showtimes:
                booked_seat_ids = uow.bookings.booked_seat_ids(st.id)
                if booked_seat_ids:
                    raise InvalidBookingError("Không thể xóa phim vì đã có suất chiếu có khách đặt vé")
            for st in showtimes:
                uow.showtimes.delete(st.id)
            uow.movies.delete(movie_id)
            uow.commit()

    def update_showtime(self, showtime_id: int, room_name: str, start_time: datetime) -> Showtime:
        with self._unit_of_work as uow:
            showtime = uow.showtimes.get_by_id(showtime_id)
            if showtime is None:
                raise ShowtimeNotFoundError("Không tìm thấy suất chiếu")
            seats = uow.seats.list_by_room(room_name.strip())
            if not seats:
                raise InvalidBookingError(f"Phòng chiếu '{room_name}' không tồn tại trong hệ thống")
            booked_seat_ids = uow.bookings.booked_seat_ids(showtime_id)
            if booked_seat_ids and room_name.strip() != showtime.room_name:
                raise InvalidBookingError("Không thể đổi phòng chiếu cho suất chiếu đã có vé đặt")
            updated = uow.showtimes.update(
                Showtime(
                    id=showtime_id,
                    movie_id=showtime.movie_id,
                    room_name=room_name.strip(),
                    start_time=start_time,
                    created_at=showtime.created_at,
                )
            )
            uow.commit()
            return updated

    def delete_showtime(self, showtime_id: int) -> None:
        with self._unit_of_work as uow:
            showtime = uow.showtimes.get_by_id(showtime_id)
            if showtime is None:
                raise ShowtimeNotFoundError("Không tìm thấy suất chiếu")
            booked_seat_ids = uow.bookings.booked_seat_ids(showtime_id)
            if booked_seat_ids:
                raise InvalidBookingError("Không thể xóa suất chiếu đã có khách đặt vé")
            uow.showtimes.delete(showtime_id)
            uow.commit()

    def list_showtimes(self, movie_id: int | None = None, show_date: date | None = None) -> list[Showtime]:
        if self._cache is not None:
            cached = self._cache.get_showtimes(movie_id, show_date)
            if cached is not None:
                return cached
        with self._unit_of_work as uow:
            showtimes = uow.showtimes.list(movie_id=movie_id, show_date=show_date)
        if self._cache is not None:
            self._cache.put_showtimes(movie_id, show_date, showtimes)
        return showtimes

    def get_showtime_seats(self, showtime_id: int) -> tuple[Showtime, list[Seat], set[int]]:
        with self._unit_of_work as uow:
            showtime = uow.showtimes.get_by_id(showtime_id)
            if showtime is None:
                raise ShowtimeNotFoundError("Showtime was not found")
            seats = uow.seats.list_by_room(showtime.room_name)
            booked_seat_ids = uow.bookings.booked_seat_ids(showtime_id)
            return showtime, seats, booked_seat_ids
