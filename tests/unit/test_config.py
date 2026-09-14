"""Tests for environment-backed application settings."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_explicit_runtime_configuration() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://user:password@localhost/cinema",
        jwt_secret_key="x" * 32,
    )

    assert settings.database_url.endswith("/cinema")
    assert settings.access_token_expire_minutes == 30


def test_settings_reject_short_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://user:password@localhost/cinema",
            jwt_secret_key="too-short",
        )
