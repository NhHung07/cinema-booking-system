from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import UserAlreadyExistsError
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.database.models import UserModel
from app.infrastructure.repositories.mappers import to_user


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return to_user(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return to_user(model) if model else None

    def add(self, user: User) -> User:
        model = UserModel(email=user.email, password_hash=user.password_hash, full_name=user.full_name)
        self._session.add(model)
        try:
            self._session.flush()
        except IntegrityError as exc:
            self._session.rollback()
            raise UserAlreadyExistsError("Email is already registered") from exc
        return to_user(model)
