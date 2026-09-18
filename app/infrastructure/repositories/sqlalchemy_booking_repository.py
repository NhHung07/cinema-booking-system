from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import SeatAlreadyBookedError
from app.domain.entities.booking import Booking
from app.domain.repositories.booking_repository import BookingRepository
from app.infrastructure.database.models import BookingModel, BookingSeatModel
from app.infrastructure.repositories.mappers import to_booking


class SQLAlchemyBookingRepository(BookingRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, booking: Booking) -> Booking:
        model = BookingModel(user_id=booking.user_id, showtime_id=booking.showtime_id, status=booking.status.value)
        self._session.add(model)
        self._session.flush()
        return to_booking(model)

    def add_seats(self, booking_id: int, showtime_id: int, seat_ids: list[int]) -> None:
        self._session.add_all(
            [BookingSeatModel(booking_id=booking_id, showtime_id=showtime_id, seat_id=seat_id) for seat_id in seat_ids]
        )
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise SeatAlreadyBookedError("At least one seat is already booked for this showtime") from exc

    def get_by_id(self, booking_id: int) -> Booking | None:
        model = self._session.scalar(
            select(BookingModel)
            .options(selectinload(BookingModel.booking_seats))
            .where(BookingModel.id == booking_id)
        )
        return to_booking(model) if model else None

    def list_by_user_id(self, user_id: int) -> list[Booking]:
        models = self._session.scalars(
            select(BookingModel)
            .options(selectinload(BookingModel.booking_seats))
            .where(BookingModel.user_id == user_id)
            .order_by(BookingModel.created_at.desc(), BookingModel.id.desc())
        ).all()
        return [to_booking(model) for model in models]

    def booked_seat_ids(self, showtime_id: int) -> set[int]:
        ids = self._session.scalars(
            select(BookingSeatModel.seat_id).where(BookingSeatModel.showtime_id == showtime_id)
        ).all()
        return set(ids)

    def cancel_and_release_seats(self, booking: Booking) -> None:
        self._session.execute(delete(BookingSeatModel).where(BookingSeatModel.booking_id == booking.id))
        model = self._session.get(BookingModel, booking.id)
        if model is not None:
            model.status = "CANCELLED"
            self._session.flush()
