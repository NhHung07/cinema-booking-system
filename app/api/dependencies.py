from collections.abc import Generator
from time import perf_counter
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.services.auth_service import AuthService
from app.application.services.booking_service import BookingService
from app.application.services.catalog_service import CatalogService
from app.core.config import Settings
from app.core.exceptions import InvalidTokenError
from app.core.security import decode_access_token
from app.domain.entities.user import User
from app.infrastructure.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.infrastructure.observability import booking_scope, booking_stage

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_session(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_unit_of_work(session: Annotated[Session, Depends(get_session)]) -> SQLAlchemyUnitOfWork:
    return SQLAlchemyUnitOfWork(session)


def get_auth_service(
    unit_of_work: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(unit_of_work, settings)


def get_catalog_service(
    request: Request,
    unit_of_work: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
) -> CatalogService:
    return CatalogService(unit_of_work, request.app.state.catalog_cache)


def get_booking_service(
    unit_of_work: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
) -> BookingService:
    return BookingService(unit_of_work)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    return _require_user(session, _token_user_id(credentials, settings))


def _token_user_id(credentials: HTTPAuthorizationCredentials | None, settings: Settings) -> int:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidTokenError("Bearer authentication is required")
    return decode_access_token(credentials.credentials, settings)


def _require_user(session: Session, user_id: int) -> User:
    user = SQLAlchemyUserRepository(session).get_by_id(user_id)
    if user is None:
        raise InvalidTokenError("Token user no longer exists")
    return user


def get_booking_user_id(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> int:
    user_id = _token_user_id(credentials, settings)
    with booking_stage("auth_db"):
        if settings.booking_split_auth:
            with request.app.state.session_factory() as auth_session:
                _require_user(auth_session, user_id)
        else:
            _require_user(session, user_id)
    if booking_scope.get():
        request.state.booking_auth_done = perf_counter()
    return user_id


CurrentUser = Annotated[User, Depends(get_current_user)]
