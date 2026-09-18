from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.movie import Movie
from app.domain.repositories.movie_repository import MovieRepository
from app.infrastructure.database.models import MovieModel
from app.infrastructure.repositories.mappers import to_movie


class SQLAlchemyMovieRepository(MovieRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def list(self) -> list[Movie]:
        models = self._session.scalars(select(MovieModel).order_by(MovieModel.release_date.desc(), MovieModel.id)).all()
        return [to_movie(model) for model in models]

    def get_by_id(self, movie_id: int) -> Movie | None:
        model = self._session.get(MovieModel, movie_id)
        return to_movie(model) if model else None
