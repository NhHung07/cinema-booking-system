from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_catalog_service
from app.application.schemas.catalog import SeatAvailabilityResponse, SeatResponse, ShowtimeResponse
from app.application.services.catalog_service import CatalogService

router = APIRouter(prefix="/showtimes", tags=["Showtimes"])


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
