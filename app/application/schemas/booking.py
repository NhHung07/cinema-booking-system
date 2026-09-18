from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.entities.booking import BookingStatus


class BookingCreateRequest(BaseModel):
    showtime_id: int = Field(gt=0)
    seat_ids: list[int] = Field(min_length=1)

    @field_validator("seat_ids")
    @classmethod
    def seat_ids_must_be_unique_and_positive(cls, value: list[int]) -> list[int]:
        if any(seat_id <= 0 for seat_id in value):
            raise ValueError("seat_ids must contain positive integers")
        if len(set(value)) != len(value):
            raise ValueError("seat_ids must not contain duplicates")
        return value


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    showtime_id: int
    status: BookingStatus
    created_at: datetime | None
    seat_ids: list[int]
