from collections.abc import Callable

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def create_session_factory(database_url: str) -> Callable[[], Session]:
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def build_session_factory(settings: Settings | None = None) -> Callable[[], Session]:
    configured_settings = settings or get_settings()
    return create_session_factory(configured_settings.database_url)


SessionLocal = build_session_factory()
