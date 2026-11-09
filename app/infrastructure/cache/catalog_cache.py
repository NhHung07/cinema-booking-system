from datetime import date
from typing import Any

from pydantic import TypeAdapter
from redis import Redis
from redis.exceptions import RedisError

from app.domain.entities.movie import Movie
from app.domain.entities.showtime import Showtime
from app.infrastructure.observability import CACHE_OPERATIONS

MOVIES = TypeAdapter(list[Movie])
MOVIE = TypeAdapter(Movie)
SHOWTIMES = TypeAdapter(list[Showtime])


class RedisCatalogCache:
    """Cache danh mục; lỗi kết nối hoặc dữ liệu hỏng được xem như cache miss."""

    def __init__(self, client: Redis, namespace: str, ttl: int = 120):
        self._client = client
        self._prefix = f"cinema:catalog:v1:{namespace}:"
        self._ttl = ttl

    def close(self) -> None:
        self._client.close()

    def _read(self, key: str, adapter: TypeAdapter) -> Any:
        try:
            data = self._client.get(self._prefix + key)
            result = adapter.validate_json(data) if data is not None else None
            CACHE_OPERATIONS.labels("hit" if result is not None else "miss").inc()
            return result
        except (RedisError, OSError, ValueError, TypeError):
            CACHE_OPERATIONS.labels("error").inc()
            return None

    def _write(self, key: str, adapter: TypeAdapter, value: Any) -> None:
        try:
            self._client.set(self._prefix + key, adapter.dump_json(value), ex=self._ttl)
        except (RedisError, OSError, ValueError, TypeError):
            CACHE_OPERATIONS.labels("write_error").inc()

    def get_movies(self) -> list[Movie] | None:
        return self._read("movies:list", MOVIES)

    def put_movies(self, movies: list[Movie]) -> None:
        self._write("movies:list", MOVIES, movies)

    def get_movie(self, movie_id: int) -> Movie | None:
        return self._read(f"movies:{movie_id}", MOVIE)

    def put_movie(self, movie: Movie) -> None:
        self._write(f"movies:{movie.id}", MOVIE, movie)

    @staticmethod
    def _showtime_key(movie_id: int | None, show_date: date | None) -> str:
        return f"showtimes:movie={movie_id if movie_id is not None else 'all'}:date={show_date.isoformat() if show_date else 'all'}"

    def get_showtimes(self, movie_id: int | None, show_date: date | None) -> list[Showtime] | None:
        return self._read(self._showtime_key(movie_id, show_date), SHOWTIMES)

    def put_showtimes(self, movie_id: int | None, show_date: date | None, showtimes: list[Showtime]) -> None:
        self._write(self._showtime_key(movie_id, show_date), SHOWTIMES, showtimes)
