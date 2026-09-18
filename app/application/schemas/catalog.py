from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    duration_minutes: int
    release_date: date
    created_at: datetime | None


class ShowtimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    start_time: datetime
    room_name: str
    created_at: datetime | None


class SeatResponse(BaseModel):
    seat_id: int
    seat_number: str
    available: bool


class SeatAvailabilityResponse(BaseModel):
    showtime_id: int
    seats: list[SeatResponse]
