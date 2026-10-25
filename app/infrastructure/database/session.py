from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def create_session_factory(database_url: str, settings: Settings | None = None) -> Callable[[], Session]:
    options = {}
    if settings is not None and database_url.startswith("postgresql"):
        options = dict(pool_size=settings.db_pool_size, max_overflow=settings.db_max_overflow,
                       pool_timeout=settings.db_pool_timeout)
    engine = create_engine(database_url, pool_pre_ping=True, **options)
    if settings is not None and settings.metrics_enabled:
        from app.infrastructure.observability import instrument_engine
        instrument_engine(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def build_session_factory(settings: Settings | None = None) -> Callable[[], Session]:
    configured_settings = settings or get_settings()
    return create_session_factory(configured_settings.database_url, configured_settings)


SessionLocal = build_session_factory()
