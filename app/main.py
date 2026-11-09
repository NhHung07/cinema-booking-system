from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import (
    analytics_router,
    auth_router,
    bookings_router,
    movies_router,
    showtimes_router,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AdminAccessRequiredError,
    AdminBookingForbiddenError,
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
from app.application.ports.catalog_cache import CatalogCache


def _error_response(status_code: int, detail: str, headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(_: Request, exc: ApplicationError) -> JSONResponse:
        if isinstance(exc, (UserAlreadyExistsError, SeatAlreadyBookedError)):
            return _error_response(409, str(exc))
        if isinstance(exc, (MovieNotFoundError, ShowtimeNotFoundError, SeatNotFoundError, BookingNotFoundError)):
            return _error_response(404, str(exc))
        if isinstance(exc, (UnauthorizedBookingAccessError, AdminAccessRequiredError, AdminBookingForbiddenError)):
            return _error_response(403, str(exc))
        if isinstance(exc, (InvalidCredentialsError, InvalidTokenError)):
            return _error_response(401, str(exc), {"WWW-Authenticate": "Bearer"})
        if isinstance(exc, (InvalidBookingError, SeatDoesNotBelongToRoomError)):
            return _error_response(422, str(exc))
        return _error_response(400, str(exc))


def create_app(
    settings: Settings | None = None,
    session_factory: Callable[[], Session] | None = None,
    catalog_cache: CatalogCache | None = None,
) -> FastAPI:
    configured_settings = settings or get_settings()
    cache = catalog_cache
    if cache is None and configured_settings.catalog_cache_enabled:
        from redis import Redis
        from redis.backoff import NoBackoff
        from redis.retry import Retry
        from app.infrastructure.cache.catalog_cache import RedisCatalogCache
        cache = RedisCatalogCache(Redis.from_url(
            configured_settings.redis_url, socket_timeout=configured_settings.redis_timeout,
            socket_connect_timeout=configured_settings.redis_timeout,
            retry=Retry(NoBackoff(), 0),
        ), configured_settings.catalog_cache_namespace, configured_settings.catalog_cache_ttl)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            if catalog_cache is None and cache is not None:
                cache.close()
            if session_factory is None:
                app.state.session_factory.kw["bind"].dispose()

    app = FastAPI(
        title="Cinema Booking System API",
        version="1.0.0",
        description="Phase 1 cinema ticket booking backend.",
        lifespan=lifespan,
    )
    app.state.settings = configured_settings
    app.state.session_factory = session_factory or build_session_factory(configured_settings)
    app.state.catalog_cache = cache
    if configured_settings.metrics_enabled:
        from app.infrastructure.observability import MetricsMiddleware, instrument_engine
        engine = getattr(app.state.session_factory, "kw", {}).get("bind")
        if engine is not None:
            instrument_engine(engine)
        app.add_middleware(MetricsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=configured_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    static_dir = Path("static")
    uploads_dir = static_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    _register_exception_handlers(app)
    app.include_router(analytics_router)
    app.include_router(auth_router)
    app.include_router(movies_router)
    app.include_router(showtimes_router)
    app.include_router(bookings_router)

    @app.get("/health", tags=["System"], summary="Health check")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["System"])
    def readiness() -> JSONResponse:
        try:
            with app.state.session_factory() as session:
                session.execute(text("SELECT 1"))
            return JSONResponse({"status": "ready"})
        except Exception:
            return JSONResponse({"status": "not_ready"}, status_code=503)

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        if not configured_settings.metrics_enabled:
            raise HTTPException(404)
        from app.infrastructure.observability import metrics_bytes
        return Response(metrics_bytes(), media_type="text/plain; version=0.0.4; charset=utf-8")

    return app


app = create_app()
