from app.core.config import Settings
from app.core.exceptions import InvalidCredentialsError, UserAlreadyExistsError
from app.core.security import create_access_token, hash_password, verify_password
from app.domain.entities.user import User
from app.domain.repositories.unit_of_work import UnitOfWork


class AuthService:
    def __init__(self, unit_of_work: UnitOfWork, settings: Settings) -> None:
        self._unit_of_work = unit_of_work
        self._settings = settings

    def register(self, email: str, password: str, full_name: str) -> User:
        normalized_email = email.lower()
        with self._unit_of_work as uow:
            if uow.users.get_by_email(normalized_email) is not None:
                raise UserAlreadyExistsError("Email is already registered")
            user = uow.users.add(
                User(id=None, email=normalized_email, password_hash=hash_password(password), full_name=full_name)
            )
            uow.commit()
            return user

    def login(self, email: str, password: str) -> str:
        with self._unit_of_work as uow:
            user = uow.users.get_by_email(email.lower())
            if user is None or not verify_password(password, user.password_hash):
                raise InvalidCredentialsError("Incorrect email or password")
            if user.id is None:
                raise InvalidCredentialsError("User has no identifier")
            return create_access_token(user.id, self._settings)
