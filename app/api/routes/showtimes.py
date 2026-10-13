from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentAdminUser, get_catalog_service
from app.application.schemas.catalog import (
    SeatAvailabilityResponse,
    SeatResponse,
    ShowtimeCreateRequest,
    ShowtimeResponse,
    ShowtimeUpdateRequest,
)
from app.application.services.catalog_service import CatalogService

router = APIRouter(prefix="/showtimes", tags=["Showtimes"])


@router.post(
    "",
    response_model=ShowtimeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new showtime (Admin only)",
)
def create_showtime(
    request: ShowtimeCreateRequest,
    _: CurrentAdminUser,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> ShowtimeResponse:
    showtime = service.create_showtime(
        movie_id=request.movie_id,
        room_name=request.room_name,
        start_time=request.start_time,
    )
    return ShowtimeResponse.model_validate(showtime)


@router.get("", response_model=list[ShowtimeResponse], summary="List showtimes")
def list_showtimes(
    service: Annotated[CatalogService, Depends(get_catalog_service)],
    movie_id: int | None = Query(default=None, gt=0),
    show_date: date | None = Query(default=None, alias="date"),
) -> list[ShowtimeResponse]:
    return [
        ShowtimeResponse.model_validate(showtime)
        for showtime in service.list_showtimes(movie_id=movie_id, show_date=show_date)
    ]


@router.get("/{showtime_id}", response_model=ShowtimeResponse, summary="Get a showtime by ID")
def get_showtime(
    showtime_id: int,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> ShowtimeResponse:
    showtime, _, _ = service.get_showtime_seats(showtime_id)
    return ShowtimeResponse.model_validate(showtime)


@router.get("/{showtime_id}/seats", response_model=SeatAvailabilityResponse, summary="Get seat availability")
def get_showtime_seats(
    showtime_id: int,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> SeatAvailabilityResponse:
    showtime, seats, booked_seat_ids = service.get_showtime_seats(showtime_id)
    return SeatAvailabilityResponse(
        showtime_id=showtime.id,
        seats=[
            SeatResponse(seat_id=seat.id, seat_number=seat.label, available=seat.id not in booked_seat_ids)
            for seat in seats
        ],
    )


@router.put(
    "/{showtime_id}",
    response_model=ShowtimeResponse,
    summary="Update a showtime (Admin only)",
)
def update_showtime(
    showtime_id: int,
    request: ShowtimeUpdateRequest,
    _: CurrentAdminUser,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> ShowtimeResponse:
    showtime = service.update_showtime(
        showtime_id=showtime_id,
        room_name=request.room_name,
        start_time=request.start_time,
    )
    return ShowtimeResponse.model_validate(showtime)


@router.delete(
    "/{showtime_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a showtime (Admin only)",
)
def delete_showtime(
    showtime_id: int,
    _: CurrentAdminUser,
    service: Annotated[CatalogService, Depends(get_catalog_service)],
) -> dict[str, str]:
    service.delete_showtime(showtime_id)
    return {"message": "Đã xóa suất chiếu thành công"}
