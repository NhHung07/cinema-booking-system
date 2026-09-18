from abc import ABC, abstractmethod

from app.domain.entities.seat import Seat


class SeatRepository(ABC):
    @abstractmethod
    def list_by_room(self, room_name: str) -> list[Seat]: ...

    @abstractmethod
    def get_by_ids(self, seat_ids: list[int]) -> list[Seat]: ...
