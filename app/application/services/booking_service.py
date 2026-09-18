from app.core.exceptions import (
    BookingNotFoundError,
    InvalidBookingError,
    SeatDoesNotBelongToRoomError,
    SeatNotFoundError,
    ShowtimeNotFoundError,
    UnauthorizedBookingAccessError,
)
from app.domain.entities.booking import Booking, BookingStatus
from app.domain.repositories.unit_of_work import UnitOfWork


class BookingService:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    def create_booking(self, user_id: int, showtime_id: int, seat_ids: list[int]) -> Booking:
        unique_seat_ids = list(dict.fromkeys(seat_ids))
        if not unique_seat_ids or len(unique_seat_ids) != len(seat_ids):
            raise InvalidBookingError("At least one unique seat is required")

        with self._unit_of_work as uow:
            showtime = uow.showtimes.get_by_id(showtime_id)
            if showtime is None:
                raise ShowtimeNotFoundError("Showtime was not found")

            seats = uow.seats.get_by_ids(unique_seat_ids)
            found_ids = {seat.id for seat in seats}
            if any(seat_id not in found_ids for seat_id in unique_seat_ids):
                raise SeatNotFoundError("One or more seats were not found")
            if any(seat.room_name != showtime.room_name for seat in seats):
                raise SeatDoesNotBelongToRoomError("Every seat must belong to the showtime room")

            booking = uow.bookings.add(Booking(id=None, user_id=user_id, showtime_id=showtime_id))
            if booking.id is None:
                raise InvalidBookingError("Booking repository did not assign an identifier")
            # The database's UNIQUE(showtime_id, seat_id) constraint is the final
            # double-booking guard; the repository maps a constraint violation to
            # SeatAlreadyBookedError.
            uow.bookings.add_seats(booking.id, showtime_id, unique_seat_ids)
            uow.commit()
            booking.seat_ids = unique_seat_ids
            return booking

    def get_user_bookings(self, user_id: int) -> list[Booking]:
        with self._unit_of_work as uow:
            return uow.bookings.list_by_user_id(user_id)

    def get_booking(self, user_id: int, booking_id: int) -> Booking:
        with self._unit_of_work as uow:
            booking = uow.bookings.get_by_id(booking_id)
            self._ensure_owner(booking, user_id)
            return booking

    def cancel_booking(self, user_id: int, booking_id: int) -> Booking:
        with self._unit_of_work as uow:
            booking = uow.bookings.get_by_id(booking_id)
            self._ensure_owner(booking, user_id)
            assert booking is not None  # narrows the optional type after _ensure_owner
            if booking.status == BookingStatus.CANCELLED:
                return booking
            uow.bookings.cancel_and_release_seats(booking)
            uow.commit()
            booking.status = BookingStatus.CANCELLED
            booking.seat_ids = []
            return booking

    @staticmethod
    def _ensure_owner(booking: Booking | None, user_id: int) -> None:
        if booking is None:
            raise BookingNotFoundError("Booking was not found")
        if booking.user_id != user_id:
            raise UnauthorizedBookingAccessError("You cannot access another user's booking")
