from abc import ABC, abstractmethod

from app.domain.entities.movie import Movie


class MovieRepository(ABC):
    @abstractmethod
    def list(self) -> list[Movie]: ...

    @abstractmethod
    def get_by_id(self, movie_id: int) -> Movie | None: ...

    @abstractmethod
    def add(self, movie: Movie) -> Movie: ...

    @abstractmethod
    def update(self, movie: Movie) -> Movie: ...

    @abstractmethod
    def delete(self, movie_id: int) -> None: ...
