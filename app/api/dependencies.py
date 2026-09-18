from collections.abc import Generator
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
    unit_of_work: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
) -> CatalogService:
    return CatalogService(unit_of_work)


def get_booking_service(
    unit_of_work: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
) -> BookingService:
    return BookingService(unit_of_work)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidTokenError("Bearer authentication is required")
    user_id = decode_access_token(credentials.credentials, settings)
    user = SQLAlchemyUserRepository(session).get_by_id(user_id)
    if user is None:
        raise InvalidTokenError("Token user no longer exists")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
