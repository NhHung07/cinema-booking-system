from abc import ABC, abstractmethod

from app.domain.entities.movie import Movie


class MovieRepository(ABC):
    @abstractmethod
    def list(self) -> list[Movie]: ...

    @abstractmethod
    def get_by_id(self, movie_id: int) -> Movie | None: ...
