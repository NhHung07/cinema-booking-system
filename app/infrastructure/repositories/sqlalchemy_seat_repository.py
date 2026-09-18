from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.seat import Seat
from app.domain.repositories.seat_repository import SeatRepository
from app.infrastructure.database.models import SeatModel
from app.infrastructure.repositories.mappers import to_seat


class SQLAlchemySeatRepository(SeatRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_by_room(self, room_name: str) -> list[Seat]:
        models = self._session.scalars(
            select(SeatModel).where(SeatModel.room_name == room_name).order_by(SeatModel.row, SeatModel.number)
        ).all()
        return [to_seat(model) for model in models]

    def get_by_ids(self, seat_ids: list[int]) -> list[Seat]:
        if not seat_ids:
            return []
        models = self._session.scalars(select(SeatModel).where(SeatModel.id.in_(seat_ids))).all()
        return [to_seat(model) for model in models]
