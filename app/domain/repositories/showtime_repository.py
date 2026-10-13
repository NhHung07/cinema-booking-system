from abc import ABC, abstractmethod
from datetime import date

from app.domain.entities.showtime import Showtime


class ShowtimeRepository(ABC):
    @abstractmethod
    def list(self, movie_id: int | None = None, show_date: date | None = None) -> list[Showtime]: ...

    @abstractmethod
    def get_by_id(self, showtime_id: int) -> Showtime | None: ...

    @abstractmethod
    def add(self, showtime: Showtime) -> Showtime: ...

    @abstractmethod
    def update(self, showtime: Showtime) -> Showtime: ...

    @abstractmethod
    def delete(self, showtime_id: int) -> None: ...
