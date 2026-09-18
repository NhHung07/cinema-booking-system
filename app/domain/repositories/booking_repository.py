from abc import ABC, abstractmethod

from app.domain.entities.booking import Booking


class BookingRepository(ABC):
    @abstractmethod
    def add(self, booking: Booking) -> Booking: ...

    @abstractmethod
    def add_seats(self, booking_id: int, showtime_id: int, seat_ids: list[int]) -> None: ...

    @abstractmethod
    def get_by_id(self, booking_id: int) -> Booking | None: ...

    @abstractmethod
    def list_by_user_id(self, user_id: int) -> list[Booking]: ...

    @abstractmethod
    def booked_seat_ids(self, showtime_id: int) -> set[int]: ...

    @abstractmethod
    def cancel_and_release_seats(self, booking: Booking) -> None: ...
