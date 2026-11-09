from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình runtime được nạp từ biến môi trường (environment variables) hoặc file .env."""

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/cinema"
    jwt_secret_key: str = "change-me-in-development"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_allowed_origins: str = "http://localhost:5173"
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: float = Field(default=30, gt=0)
    catalog_cache_enabled: bool = False
    catalog_cache_namespace: str = Field(default="default", pattern=r"^[a-zA-Z0-9_-]+$")
    catalog_cache_ttl: int = Field(default=120, ge=1)
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_timeout: float = Field(default=0.1, gt=0)
    metrics_enabled: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origins(self) -> list[str]:
        """Trả về danh sách browser origin đã cấu hình dưới dạng phân cách bởi dấu phẩy."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
