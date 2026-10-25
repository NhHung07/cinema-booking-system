import os
from time import perf_counter

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, REGISTRY, generate_latest, multiprocess
from sqlalchemy import event
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

REQUESTS = Counter("cinema_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram("cinema_http_duration_seconds", "HTTP latency", ["method", "route"],
                    buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2, 5, 10))
SQL_QUERIES = Counter("cinema_sql_queries_total", "SQL statements executed")
SQL_TIME = Histogram("cinema_sql_duration_seconds", "SQL execution duration")
POOL_ACTIVE = Gauge("cinema_db_connections", "Checked-out API connections", multiprocess_mode="livesum")
POOL_TIMEOUTS = Counter("cinema_db_pool_timeouts_total", "Pool acquisition timeouts")
CACHE_OPERATIONS = Counter("cinema_cache_operations_total", "Catalog cache operations", ["outcome"])
WORKER_REQUESTS = Counter("cinema_worker_requests_total", "Requests by worker", ["pid"])


def metrics_bytes() -> bytes:
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    return generate_latest(REGISTRY)


def instrument_engine(engine) -> None:
    if getattr(engine, "_cinema_instrumented", False):
        return
    engine._cinema_instrumented = True

    @event.listens_for(engine, "before_cursor_execute")
    def before(conn, cursor, statement, parameters, context, executemany):
        context._cinema_started = perf_counter()
        SQL_QUERIES.inc()

    @event.listens_for(engine, "after_cursor_execute")
    def after(conn, cursor, statement, parameters, context, executemany):
        SQL_TIME.observe(perf_counter() - context._cinema_started)

    @event.listens_for(engine, "handle_error")
    def failed(context):
        started = getattr(context.execution_context, "_cinema_started", None)
        if started is not None:
            SQL_TIME.observe(perf_counter() - started)

    @event.listens_for(engine, "checkout")
    def checkout(*args):
        POOL_ACTIVE.inc()

    @event.listens_for(engine, "checkin")
    def checkin(*args):
        POOL_ACTIVE.dec()


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started, status = perf_counter(), 500

        async def capture(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, capture)
        except PoolTimeoutError:
            POOL_TIMEOUTS.inc()
            raise
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            if route not in {"/metrics", "/ready", "/health"}:
                REQUESTS.labels(scope["method"], route, str(status)).inc()
                LATENCY.labels(scope["method"], route).observe(perf_counter() - started)
                WORKER_REQUESTS.labels(str(os.getpid())).inc()
