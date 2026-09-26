from datetime import UTC, datetime, timedelta

import pytest

from app.application.services.booking_service import BookingService
from app.core.exceptions import SeatAlreadyBookedError, ShowtimeNotFoundError, UnauthorizedBookingAccessError, InvalidBookingError
from app.domain.entities import Booking, BookingStatus, Seat, Showtime


class FakeShowtimes:
    def __init__(self, showtime: Showtime | None) -> None:
        self.showtime = showtime

    def get_by_id(self, showtime_id: int) -> Showtime | None:
        return self.showtime if self.showtime and self.showtime.id == showtime_id else None


class FakeSeats:
    def __init__(self, seats: list[Seat]) -> None:
        self.seats = seats

    def get_by_ids(self, seat_ids: list[int]) -> list[Seat]:
        return [seat for seat in self.seats if seat.id in seat_ids]


class FakeBookings:
    def __init__(self) -> None:
        self.items: dict[int, Booking] = {}
        self.reserved: set[tuple[int, int]] = set()
        self.next_id = 1

    def add(self, booking: Booking) -> Booking:
        booking.id = self.next_id
        self.next_id += 1
        self.items[booking.id] = booking
        return booking

    def add_seats(self, booking_id: int, showtime_id: int, seat_ids: list[int]) -> None:
        if any((showtime_id, seat_id) in self.reserved for seat_id in seat_ids):
            self.items.pop(booking_id, None)
            raise SeatAlreadyBookedError("At least one seat is already booked for this showtime")
        self.reserved.update((showtime_id, seat_id) for seat_id in seat_ids)

    def get_by_id(self, booking_id: int) -> Booking | None:
        return self.items.get(booking_id)

    def list_by_user_id(self, user_id: int) -> list[Booking]:
        return [booking for booking in self.items.values() if booking.user_id == user_id]

    def booked_seat_ids(self, showtime_id: int) -> set[int]:
        return {seat_id for candidate_showtime_id, seat_id in self.reserved if candidate_showtime_id == showtime_id}

    def cancel_and_release_seats(self, booking: Booking) -> None:
        self.reserved.difference_update((booking.showtime_id, seat_id) for seat_id in booking.seat_ids)


class FakeUnitOfWork:
    def __init__(self, showtime: Showtime | None, seats: list[Seat]) -> None:
        self.showtimes = FakeShowtimes(showtime)
        self.seats = FakeSeats(seats)
        self.bookings = FakeBookings()
        self.committed = False

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        return None


@pytest.fixture
def fake_uow() -> FakeUnitOfWork:
    showtime = Showtime(id=10, movie_id=1, room_name="ROOM_1", start_time=datetime.now(UTC) + timedelta(hours=2))
    seats = [Seat(id=1, room_name="ROOM_1", row="A", number=1), Seat(id=2, room_name="ROOM_1", row="A", number=2)]
    return FakeUnitOfWork(showtime, seats)

# Dat ve thanh cong
def test_booking_succeeds_and_commits(fake_uow: FakeUnitOfWork) -> None:
    booking = BookingService(fake_uow).create_booking(user_id=7, showtime_id=10, seat_ids=[1, 2])

    assert booking.id == 1
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.seat_ids == [1, 2]
    assert fake_uow.committed is True

# Sai showtime
def test_booking_rejects_missing_showtime(fake_uow: FakeUnitOfWork) -> None:
    with pytest.raises(ShowtimeNotFoundError):
        BookingService(fake_uow).create_booking(user_id=7, showtime_id=999, seat_ids=[1])

# Dat ve trung
def test_booking_rejects_an_already_reserved_seat(fake_uow: FakeUnitOfWork) -> None:
    service = BookingService(fake_uow)
    service.create_booking(user_id=7, showtime_id=10, seat_ids=[1])

    with pytest.raises(SeatAlreadyBookedError):
        service.create_booking(user_id=8, showtime_id=10, seat_ids=[1])

# Khong duoc doc ve cua nguoi khac
def test_user_cannot_read_someone_elses_booking(fake_uow: FakeUnitOfWork) -> None:
    service = BookingService(fake_uow)
    booking = service.create_booking(user_id=7, showtime_id=10, seat_ids=[1])

    with pytest.raises(UnauthorizedBookingAccessError):
        service.get_booking(user_id=8, booking_id=booking.id)

# Chi huy duoc ve cua minh 
def test_cancel_releases_seats(fake_uow: FakeUnitOfWork) -> None:
    service = BookingService(fake_uow)
    booking = service.create_booking(user_id=7, showtime_id=10, seat_ids=[1])

    cancelled = service.cancel_booking(user_id=7, booking_id=booking.id)

    assert cancelled.status == BookingStatus.CANCELLED
    assert cancelled.seat_ids == []
    replacement = service.create_booking(user_id=8, showtime_id=10, seat_ids=[1])
    assert replacement.id == 2

# Khong duoc huy booking cua nguoi khac
def test_user_cannot_cancel_someone_elses_booking(fake_uow: FakeUnitOfWork) -> None:
    service = BookingService(fake_uow)
    booking = service.create_booking(user_id=7, showtime_id=10, seat_ids=[1])
    with pytest.raises(UnauthorizedBookingAccessError):
        service.cancel_booking(user_id=8, booking_id=booking.id)

# Khong dat ve khi danh sach ghe rong hoac trung lap
def test_booking_rejects_empty_or_duplicate_seats(fake_uow: FakeUnitOfWork) -> None:
    service = BookingService(fake_uow)
    
    # ghe rong
    with pytest.raises(InvalidBookingError):
        service.create_booking(user_id=7, showtime_id=10, seat_ids=[])
    # ghe trung lap
    with pytest.raises(InvalidBookingError):
        service.create_booking(user_id=7, showtime_id=10, seat_ids=[1, 1])

# Khong tao booking neu showtime da ket thuc
def test_booking_rejects_ended_showtime(fake_uow: FakeUnitOfWork) -> None:
    fake_uow.showtimes.showtime.start_time = datetime.now(UTC) - timedelta(hours=2)
    service = BookingService(fake_uow)
    with pytest.raises(InvalidBookingError):
        service.create_booking(user_id=7, showtime_id=10, seat_ids=[1])