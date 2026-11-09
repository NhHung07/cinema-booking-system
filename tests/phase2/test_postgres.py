import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import uuid

import httpx
import pytest
from redis import Redis
from sqlalchemy import create_engine, text

from experiments.phase2.dataset import DatasetSpec, build_manifest, seed_database, database_fingerprint, verify_bookings
from experiments.phase2.runtime import DatabaseAdmin
from experiments.phase2.runner import api_server, migrate

pytestmark = pytest.mark.skipif(not os.environ.get("PHASE2_ADMIN_URL"), reason="Requires dedicated PostgreSQL 16 and Redis 7")


@pytest.fixture
def database(tmp_path):
    admin = DatabaseAdmin(os.environ["PHASE2_ADMIN_URL"], uuid.uuid4().hex[:10])
    name = admin.create("test")
    url = admin.database_url(name)
    migrate(url, tmp_path / "migration.log")
    engine = create_engine(url.replace("postgresql://", "postgresql+psycopg://", 1))
    manifest = build_manifest(DatasetSpec(users=20, movies=6, rooms=2, seats_per_room=10, showtimes=40, bookings=10))
    seed_database(engine, manifest)
    try:
        yield admin, name, url, engine, manifest
    finally:
        engine.dispose()
        admin.close()


def test_template_restore_preserves_every_table(database):
    admin, name, _, engine, _ = database
    expected = database_fingerprint(engine)
    engine.dispose()
    clone = admin.create("clone", template=name)
    other = create_engine(admin.database_url(clone).replace("postgresql://", "postgresql+psycopg://", 1))
    try:
        assert database_fingerprint(other) == expected
    finally:
        other.dispose()


def test_two_workers_compete_atomically_and_cancellation_releases_seat(database, tmp_path):
    _, _, url, engine, _ = database
    from app.core.security import create_access_token
    from app.core.config import Settings
    secret = uuid.uuid4().hex * 2
    config = Settings(jwt_secret_key=secret)
    headers = [{"Authorization": "Bearer " + create_access_token(i + 1, config)} for i in range(10)]
    # Allocation 0 is not guaranteed free; select an actual free seat in the fixture.
    with engine.connect() as connection:
        seat = connection.scalar(text("SELECT s.id FROM seats s WHERE s.room_name='ROOM_1' AND NOT EXISTS (SELECT 1 FROM booking_seats b WHERE b.showtime_id=1 AND b.seat_id=s.id) LIMIT 1"))
    with api_server(url, "C", tmp_path, secret, namespace="worker_test") as (host, _):
        payload = {"showtime_id": 1, "seat_ids": [seat]}
        with ThreadPoolExecutor(max_workers=10) as pool:
            responses = list(pool.map(lambda h: httpx.post(host + "/bookings", headers=h, json=payload, timeout=10), headers))
        assert sorted(r.status_code for r in responses) == [201] + [409] * 9
        winner = next(i for i, response in enumerate(responses) if response.status_code == 201)
        booking = responses[winner].json()
        assert httpx.get(host + f"/bookings/{booking['id']}", headers=headers[winner]).status_code == 200
        assert httpx.delete(host + f"/bookings/{booking['id']}", headers=headers[winner]).status_code == 200
        assert httpx.post(host + "/bookings", headers=headers[0], json=payload).status_code == 201
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM bookings b WHERE status='CONFIRMED' AND NOT EXISTS (SELECT 1 FROM booking_seats s WHERE s.booking_id=b.id)")) == 0
            assert connection.scalar(text("SELECT count(*) FROM booking_seats WHERE showtime_id=1 AND seat_id=:seat"), {"seat": seat}) == 1


def test_redis_adapter_real_ttl_corruption_and_namespace_isolation():
    url = os.environ.get("PHASE2_REDIS_URL", "redis://127.0.0.1:36389/0")
    client = Redis.from_url(url)
    namespace = uuid.uuid4().hex
    from app.infrastructure.cache.catalog_cache import RedisCatalogCache
    first = RedisCatalogCache(client, namespace, ttl=1)
    other = RedisCatalogCache(client, namespace + "other")
    try:
        first.put_movies([])
        assert first.get_movies() == []
        assert other.get_movies() is None
        key = f"cinema:catalog:v1:{namespace}:movies:list"
        client.set(key, b"{invalid-json", ex=1)
        assert first.get_movies() is None
        first.put_movies([])
        import time
        deadline = time.monotonic() + 3
        while first.get_movies() is not None and time.monotonic() < deadline:
            time.sleep(.05)
        assert first.get_movies() is None
    finally:
        keys = list(client.scan_iter(f"cinema:catalog:v1:{namespace}*"))
        if keys:
            client.delete(*keys)
        client.close()
