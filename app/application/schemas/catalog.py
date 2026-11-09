from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class MovieCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    duration_minutes: int = Field(gt=0, le=600)
    release_date: date
    poster_url: str | None = Field(default=None, max_length=2048)


class MovieUpdateRequest(MovieCreateRequest):
    pass


class MovieResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    duration_minutes: int
    release_date: date
    poster_url: str | None = None
    created_at: datetime | None


class ImageUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    image_data: str = Field(min_length=1)


class ImageUploadResponse(BaseModel):
    image_url: str


class ShowtimeCreateRequest(BaseModel):
    movie_id: int = Field(gt=0)
    room_name: str = Field(min_length=1, max_length=50)
    start_time: datetime


class ShowtimeUpdateRequest(BaseModel):
    room_name: str = Field(min_length=1, max_length=50)
    start_time: datetime


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
