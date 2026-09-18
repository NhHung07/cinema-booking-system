from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class BookingStatus(StrEnum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class Booking:
    id: int | None
    user_id: int
    showtime_id: int
    status: BookingStatus = BookingStatus.CONFIRMED
    created_at: datetime | None = None
    seat_ids: list[int] = field(default_factory=list)


@dataclass(slots=True)
class BookingSeat:
    id: int | None
    booking_id: int
    showtime_id: int
    seat_id: int
