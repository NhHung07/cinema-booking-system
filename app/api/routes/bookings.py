from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentUser, get_booking_service
from app.application.schemas.booking import BookingCreateRequest, BookingResponse
from app.application.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book one or more seats",
)
def create_booking(
    request: BookingCreateRequest,
    current_user: CurrentUser,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    return BookingResponse.model_validate(
        service.create_booking(current_user.id, request.showtime_id, request.seat_ids)
    )


@router.get("/me", response_model=list[BookingResponse], summary="List the current user's bookings")
def get_my_bookings(
    current_user: CurrentUser,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> list[BookingResponse]:
    return [BookingResponse.model_validate(booking) for booking in service.get_user_bookings(current_user.id)]


@router.get("/{booking_id}", response_model=BookingResponse, summary="Get one of your bookings")
def get_booking(
    booking_id: int,
    current_user: CurrentUser,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    return BookingResponse.model_validate(service.get_booking(current_user.id, booking_id))


@router.delete("/{booking_id}", response_model=BookingResponse, summary="Cancel a booking and release its seats")
def cancel_booking(
    booking_id: int,
    current_user: CurrentUser,
    service: Annotated[BookingService, Depends(get_booking_service)],
) -> BookingResponse:
    return BookingResponse.model_validate(service.cancel_booking(current_user.id, booking_id))
