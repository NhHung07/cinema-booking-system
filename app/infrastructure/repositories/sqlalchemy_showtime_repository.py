from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.showtime import Showtime
from app.domain.repositories.showtime_repository import ShowtimeRepository
from app.infrastructure.database.models import ShowtimeModel
from app.infrastructure.repositories.mappers import to_showtime


class SQLAlchemyShowtimeRepository(ShowtimeRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self, movie_id: int | None = None, show_date: date | None = None) -> list[Showtime]:
        statement = select(ShowtimeModel)
        if movie_id is not None:
            statement = statement.where(ShowtimeModel.movie_id == movie_id)
        if show_date is not None:
            start = datetime.combine(show_date, time.min)
            end = start + timedelta(days=1)
            statement = statement.where(ShowtimeModel.start_time >= start, ShowtimeModel.start_time < end)
        models = self._session.scalars(statement.order_by(ShowtimeModel.start_time, ShowtimeModel.id)).all()
        return [to_showtime(model) for model in models]

    def get_by_id(self, showtime_id: int) -> Showtime | None:
        model = self._session.get(ShowtimeModel, showtime_id)
        return to_showtime(model) if model else None
