from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes import auth_router, bookings_router, movies_router, showtimes_router
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ApplicationError,
    BookingNotFoundError,
    InvalidBookingError,
    InvalidCredentialsError,
    InvalidTokenError,
    MovieNotFoundError,
    SeatAlreadyBookedError,
    SeatDoesNotBelongToRoomError,
    SeatNotFoundError,
    ShowtimeNotFoundError,
    UnauthorizedBookingAccessError,
    UserAlreadyExistsError,
)
from app.infrastructure.database.session import build_session_factory


def _error_response(status_code: int, detail: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(_: Request, exc: ApplicationError) -> JSONResponse:
        if isinstance(exc, (UserAlreadyExistsError, SeatAlreadyBookedError)):
            return _error_response(409, str(exc))
        if isinstance(exc, (MovieNotFoundError, ShowtimeNotFoundError, SeatNotFoundError, BookingNotFoundError)):
            return _error_response(404, str(exc))
        if isinstance(exc, UnauthorizedBookingAccessError):
            return _error_response(403, str(exc))
        if isinstance(exc, (InvalidCredentialsError, InvalidTokenError)):
            return _error_response(401, str(exc), {"WWW-Authenticate": "Bearer"})
        if isinstance(exc, (InvalidBookingError, SeatDoesNotBelongToRoomError)):
            return _error_response(422, str(exc))
        return _error_response(400, str(exc))


def create_app(
    settings: Settings | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> FastAPI:
    configured_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    app = FastAPI(
        title="Cinema Booking System API",
        version="1.0.0",
        description="Phase 1 cinema ticket booking backend.",
        lifespan=lifespan,
    )
    app.state.settings = configured_settings
    app.state.session_factory = session_factory or build_session_factory(configured_settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configured_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _register_exception_handlers(app)
    app.include_router(auth_router)
    app.include_router(movies_router)
    app.include_router(showtimes_router)
    app.include_router(bookings_router)

    @app.get("/health", tags=["System"], summary="Health check")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
