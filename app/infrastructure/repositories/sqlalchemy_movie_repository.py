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

    def add(self, movie: Movie) -> Movie:
        model = MovieModel(
            title=movie.title,
            description=movie.description,
            duration_minutes=movie.duration_minutes,
            release_date=movie.release_date,
            poster_url=movie.poster_url,
        )
        self._session.add(model)
        self._session.flush()
        return to_movie(model)

    def update(self, movie: Movie) -> Movie:
        model = self._session.get(MovieModel, movie.id)
        if model is not None:
            model.title = movie.title
            model.description = movie.description
            model.duration_minutes = movie.duration_minutes
            model.release_date = movie.release_date
            model.poster_url = movie.poster_url
            self._session.flush()
            return to_movie(model)
        return movie

    def delete(self, movie_id: int) -> None:
        model = self._session.get(MovieModel, movie_id)
        if model is not None:
            self._session.delete(model)
            self._session.flush()
