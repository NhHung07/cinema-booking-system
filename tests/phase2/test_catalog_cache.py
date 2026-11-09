from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import MovieModel, ShowtimeModel
from app.main import create_app


class DictionaryRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex):
        self.data[key] = value

    def close(self):
        pass


@pytest.fixture
def app_with_cache():
    from app.infrastructure.cache.catalog_cache import RedisCatalogCache

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add(MovieModel(id=1, title="Phim", description="Mô tả", duration_minutes=120, release_date=date(2030, 1, 1)))
        session.add(ShowtimeModel(id=1, movie_id=1, room_name="R1", start_time=datetime(2030, 1, 1, 10, tzinfo=UTC)))
        session.commit()
    queries = []
    event.listen(engine, "before_cursor_execute", lambda *args: queries.append(args[2]))
    app = create_app(Settings(database_url="sqlite://", metrics_enabled=True), factory,
                     catalog_cache=RedisCatalogCache(DictionaryRedis(), namespace="test"))
    with TestClient(app) as client:
        yield client, queries, factory
    engine.dispose()


def test_cached_movie_response_remains_identical_without_another_sql_query(app_with_cache):
    client, queries, _ = app_with_cache
    first = client.get("/movies")
    assert first.status_code == 200
    queries.clear()
    second = client.get("/movies")
    assert second.json() == first.json()
    assert queries == []


def test_filter_and_empty_result_cache_do_not_leak_between_queries(app_with_cache):
    client, queries, _ = app_with_cache
    assert client.get("/showtimes?movie_id=1").json()[0]["id"] == 1
    assert client.get("/showtimes?movie_id=2").json() == []
    queries.clear()
    assert client.get("/showtimes?movie_id=2").json() == []
    assert queries == []
    assert client.get("/showtimes?date=2030-01-02").json() == []
    assert len(client.get("/showtimes?date=2030-01-01").json()) == 1


def test_missing_movie_is_not_cached(app_with_cache):
    client, queries, factory = app_with_cache
    assert client.get("/movies/2").status_code == 404
    with factory() as session:
        session.add(MovieModel(id=2, title="New", description="x", duration_minutes=100, release_date=date(2030, 1, 1)))
        session.commit()
    assert client.get("/movies/2").json()["title"] == "New"


def test_readiness_and_metrics_use_route_templates(app_with_cache):
    client, _, _ = app_with_cache
    assert client.get("/ready").status_code == 200
    client.get("/movies/1")
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert 'route="/movies/{movie_id}"' in metrics.text
    assert 'route="/movies/1"' not in metrics.text
    assert "cinema_sql_queries_total" in metrics.text


def test_default_app_does_not_expose_metrics():
    with TestClient(create_app(Settings(database_url="sqlite://"))) as client:
        assert client.get("/metrics").status_code == 404


def test_readiness_reports_database_failure():
    def broken():
        raise OSError("private database details")
    with TestClient(create_app(Settings(database_url="sqlite://"), broken)) as client:
        response = client.get("/ready")
        assert response.status_code == 503
        assert "private" not in response.text


def test_cache_connection_errors_and_corrupt_payloads_fall_back_to_database(app_with_cache):
    from redis.exceptions import ConnectionError
    client, queries, _ = app_with_cache
    cache = client.app.state.catalog_cache
    cache._client.data["cinema:catalog:v1:test:movies:list"] = b"not-json"
    assert client.get("/movies").json()[0]["title"] == "Phim"

    class BrokenRedis:
        def get(self, key):
            raise ConnectionError("unavailable")

        def set(self, *args, **kwargs):
            raise ConnectionError("unavailable")

    cache._client = BrokenRedis()
    queries.clear()
    assert client.get("/movies").json()[0]["title"] == "Phim"
    assert len(queries) == 1
    assert client.get("/ready").status_code == 200
