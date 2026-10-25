import argparse
from contextlib import contextmanager, ExitStack
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tarfile
import time
from urllib.parse import urlsplit

import httpx
import psycopg
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError
from sqlalchemy import create_engine

from experiments.phase2.collect import ResourceSampler, metric_delta
from experiments.phase2.config import VARIANTS, RunSpec, build_matrix, variant_environment
from experiments.phase2.dataset import DatasetSpec, build_manifest, database_fingerprint, seed_database, verify_bookings
from experiments.phase2.environment import inspect_environment, preflight, write_json
from experiments.phase2.results import aggregate_runs
from experiments.phase2.runtime import DatabaseAdmin, Processes, free_port, local_postgres, start_redis

ROOT = Path(__file__).resolve().parents[2]


def sqlalchemy_url(url: str) -> str:
    return url.replace("postgresql://", "postgresql+psycopg://", 1)


def migrate(url: str, log: Path):
    env = dict(os.environ, DATABASE_URL=sqlalchemy_url(url))
    with log.open("wb") as output:
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT,
                       env=env, check=True, stdout=output, stderr=subprocess.STDOUT)


def wait_ready(host: str, process, timeout: float = 30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("API exited before readiness; inspect api.log")
        try:
            if httpx.get(host + "/ready", timeout=.5, trust_env=False).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(.1)
    raise RuntimeError("API readiness timed out; inspect api.log")


def check_redis(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme != "redis" or parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or parsed.query or parsed.fragment:
        raise ValueError("Redis must be a loopback service without URL overrides")
    with Redis.from_url(url, socket_timeout=.1, socket_connect_timeout=.1) as client:
        deadline = time.monotonic() + 5
        while True:
            try:
                version = client.info("server")["redis_version"]
                if version.split(".")[0] != "7":
                    raise RuntimeError("Redis 7 is required")
                return version
            except (RedisConnectionError, RedisTimeoutError, OSError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Redis startup failed") from None
                time.sleep(.1)


@contextmanager
def api_server(url: str, variant: str, directory: Path, secret: str, namespace: str,
               redis_url: str | None = None):
    processes = Processes()
    directory.mkdir(parents=True, exist_ok=True)
    try:
        env = dict(os.environ, **variant_environment(variant, namespace))
        metrics = directory / "metrics"
        metrics.mkdir()
        env.update(DATABASE_URL=sqlalchemy_url(url), JWT_SECRET_KEY=secret,
                   PROMETHEUS_MULTIPROC_DIR=str(metrics.resolve()))
        redis_pid = None
        if VARIANTS[variant][1]:
            if redis_url is None:
                redis_url, redis_pid = start_redis(processes, directory)
            version = check_redis(redis_url)
            env["REDIS_URL"] = redis_url
            write_json(directory / "redis-version.json", {"version": version, "owned_process": redis_pid})
        port = free_port()
        host = f"http://127.0.0.1:{port}"
        process = processes.start([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                                   "--port", str(port), "--workers", str(VARIANTS[variant][0]), "--no-access-log"],
                                  directory / "api.log", env)
        wait_ready(host, process)
        yield host, {"api": process.pid, "redis": redis_pid}
    finally:
        processes.close()


def source_files() -> list[Path]:
    files = []
    for name in ["app", "migrations", "experiments", "tests", "scripts", "requirements.txt", "alembic.ini", "pytest.ini"]:
        path = ROOT / name
        files.extend([p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"] if path.is_dir() else [path])
    return sorted(files)


def source_fingerprints() -> dict:
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files()}


def capture_source(directory: Path) -> dict:
    fingerprints = source_fingerprints()
    write_json(directory / "source-manifest.json", fingerprints)
    with tarfile.open(directory / "source.tar.gz", "w:gz") as archive:
        for path in source_files():
            archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    return fingerprints


def prime(host: str, manifest: dict):
    with httpx.Client(base_url=host, timeout=5, trust_env=False) as client:
        paths = ["/movies"]
        for movie in range(1, min(50, manifest["spec"]["movies"]) + 1):
            paths.extend([f"/movies/{movie}", f"/showtimes?movie_id={movie}", f"/showtimes?movie_id={movie}&date=2030-01-01"])
        for path in paths:
            if client.get(path).status_code != 200:
                raise RuntimeError("Catalog priming failed")


def run_one(admin: DatabaseAdmin, snapshot: str, manifest: dict, fingerprint: dict,
            spec: RunSpec, directory: Path, redis_url: str | None, postgres_pid: int | None) -> dict:
    directory.mkdir()
    write_json(directory / "spec.json", spec.to_dict())
    write_json(directory / "state.json", {"status": "running", "started_at": datetime.now(timezone.utc).isoformat()})
    database, engine = None, None
    result = dict(spec.to_dict(), valid=False)
    processes = Processes()
    try:
        database = admin.create("r" + directory.name, template=snapshot)
        url = admin.database_url(database)
        engine = create_engine(sqlalchemy_url(url))
        if database_fingerprint(engine) != fingerprint:
            raise RuntimeError("Snapshot fingerprint mismatch")
        engine.dispose()
        secret = secrets.token_hex(32)
        with api_server(url, spec.variant, directory, secret, f"{admin.owner}_{directory.name}", redis_url) as (host, roots):
            if spec.scenario in {"R1", "R4"}:
                prime(host, manifest)
            result.update(_measure(host, roots, postgres_pid, url, spec, directory, processes, secret))
        integrity = verify_bookings(engine, manifest["spec"]["bookings"])
        acknowledged = result.get("acknowledged_bookings", 0)
        extra = integrity["new_bookings"] - acknowledged
        timeout_count = int(result.get("all_statuses", {}).get("0", 0))
        integrity["unacknowledged_commits"] = extra
        integrity["acknowledgements_consistent"] = 0 <= extra <= timeout_count
        result["integrity"] = integrity
        result["valid"] = bool(result.get("valid")) and integrity["valid"] and integrity["acknowledgements_consistent"]
    except (Exception, KeyboardInterrupt) as exc:
        result.update(valid=False, infrastructure_error=type(exc).__name__)
        if isinstance(exc, KeyboardInterrupt):
            raise
    finally:
        result["cleanup_errors"] = []
        actions = [("processes", processes.close)]
        if engine is not None:
            actions.append(("engine", engine.dispose))
        if database is not None:
            actions.append(("database", lambda: admin.drop(database)))
        # Persist first: cleanup can fail independently (including a database outage).
        write_json(directory / "result.json", result)
        for name, action in actions:
            try:
                action()
            except Exception as exc:
                result["cleanup_errors"].append(f"{name}:{type(exc).__name__}")
                result["valid"] = False
        write_json(directory / "result.json", result)
        write_json(directory / "state.json", {"status": "complete" if result.get("valid") else "invalid",
                                               "finished_at": datetime.now(timezone.utc).isoformat()})
    return result


def _measure(host, roots, postgres_pid, url, spec, directory, processes, secret):
    env = dict(os.environ, JWT_SECRET_KEY=secret)
    load = processes.start([sys.executable, "-m", "experiments.phase2.load", "--host", host,
                            "--spec", str(directory / "spec.json"), "--manifest", str(directory.parent / "dataset.json"),
                            "--output", str(directory / "load.json")], directory / "load.log", env)
    sampler = ResourceSampler(dict(roots, postgres=postgres_pid, load=load.pid), url, directory / "resources.csv")
    sampler.start()
    try:
        load.wait(timeout=spec.warmup + spec.duration + spec.drain + 60)
        if load.returncode:
            raise RuntimeError("Load generator failed; inspect load.log")
    finally:
        sampler.stop()
    result = json.loads((directory / "load.json").read_text())
    result["server_metrics"] = metric_delta(result.pop("metrics_before"), result.pop("metrics_after"))
    # Keep raw metrics evidence independently of summary calculations.
    raw = json.loads((directory / "load.json").read_text())
    (directory / "metrics-before.txt").write_text(raw["metrics_before"])
    (directory / "metrics-after.txt").write_text(raw["metrics_after"])
    resources = sampler.summary(result["measurement_start_monotonic"], result["measurement_end_monotonic"])
    result["resources"] = resources
    if resources["errors"] or resources["generator_saturated"] or resources["api_process_changed"] or resources["required_service_missing"]:
        result["valid"] = False
    return result


def finalize_experiment(admin, output: Path, metadata: dict, rows: list[dict]) -> dict:
    errors = metadata.setdefault("cleanup_errors", [])
    if admin is not None:
        try:
            admin.close()
        except Exception as exc:
            errors.append("databases:" + type(exc).__name__)
    metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary = aggregate_runs(rows, len(metadata["matrix"]), expected_matrix=metadata["matrix"])
    summary["complete"] = summary["complete"] and not errors and not metadata.get("failure_type")
    summary.update(canonical=metadata["canonical"], cleanup_errors=errors,
                   primary_complete=summary["complete"] and metadata["canonical"] and metadata["profile"] == "full" and len(metadata["matrix"]) == 144)
    metadata["status"] = "complete" if summary["complete"] else "incomplete"
    write_json(output / "experiment.json", metadata)
    write_json(output / "summary.json", summary)
    return summary


def execute(args) -> int:
    if args.validation_only and args.profile != "smoke":
        raise ValueError("Validation mode cannot produce a canonical full experiment")
    if (args.small_data or args.limit_runs) and not args.validation_only:
        raise ValueError("Reduced runs/data require explicit --validation-only")
    if args.limit_runs is not None and args.limit_runs < 1:
        raise ValueError("--limit-runs must be positive")
    external = os.environ.get("PHASE2_ADMIN_URL")
    redis_url = os.environ.get("PHASE2_REDIS_URL")
    if (external or redis_url) and not args.validation_only:
        raise ValueError("Canonical runs manage their own local PostgreSQL and Redis processes")
    environment = inspect_environment()
    preflight(environment, args.validation_only)
    output = args.output_root.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Store experiment results outside the source repository")
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "environment.json", environment)
    source = capture_source(output)
    (output / "requirements.freeze.txt").write_text("\n".join(environment["packages"]) + "\n")
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, environment["cpu_affinity"][:4])
    runs = build_matrix(args.profile)
    if args.limit_runs:
        runs = runs[:args.limit_runs]
    metadata = {"profile": args.profile, "canonical": not args.validation_only,
                "session_id": secrets.token_hex(16), "matrix": [r.to_dict() for r in runs],
                "dataset": "reduced-validation" if args.small_data else "standard",
                "started_at": datetime.now(timezone.utc).isoformat()}
    write_json(output / "experiment.json", metadata)
    rows = []
    try:
        with ExitStack() as stack:
            if external:
                admin_url, postgres_pid = external, None
            else:
                admin_url, postgres_pid = stack.enter_context(local_postgres(output))
            with psycopg.connect(admin_url) as connection:
                version = int(connection.execute("SHOW server_version_num").fetchone()[0])
                if not 160000 <= version < 170000:
                    raise RuntimeError("PostgreSQL 16 is required")
                metadata["postgres_version_num"] = version
            admin = DatabaseAdmin(admin_url, metadata["session_id"][:10])

            def close_databases():
                try:
                    admin.close()
                except Exception as exc:
                    metadata.setdefault("cleanup_errors", []).append("databases:" + type(exc).__name__)

            stack.callback(close_databases)
            snapshot = admin.create("snapshot")
            url = admin.database_url(snapshot)
            migrate(url, output / "migration.log")
            dataset = DatasetSpec(users=200, movies=50, rooms=5, seats_per_room=100, showtimes=500, bookings=1000) if args.small_data else DatasetSpec()
            manifest = build_manifest(dataset)
            write_json(output / "dataset.json", manifest)
            engine = create_engine(sqlalchemy_url(url))
            try:
                seed_database(engine, manifest)
                fingerprint = database_fingerprint(engine)
                write_json(output / "snapshot.json", fingerprint)
            finally:
                engine.dispose()
            for index, spec in enumerate(runs, 1):
                current = inspect_environment()
                if (current["packages_sha256"] != environment["packages_sha256"]
                    or current["cpu_quota"] != environment["cpu_quota"]
                    or current["cpu_model"] != environment["cpu_model"]
                    or current["cpu_affinity"] != environment["cpu_affinity"][:4]
                    or source_fingerprints() != source):
                    raise RuntimeError("Experiment environment changed")
                print(f"[{index}/{len(runs)}] {spec.variant} {spec.scenario} users={spec.users} repeat={spec.repeat}", flush=True)
                row = run_one(admin, snapshot, manifest, fingerprint, spec, output / f"{index:03}", redis_url, postgres_pid)
                rows.append(row)
                summary = aggregate_runs(rows, len(runs), expected_matrix=metadata["matrix"])
                summary["canonical"] = metadata["canonical"]
                summary["primary_complete"] = summary["complete"] and metadata["canonical"] and args.profile == "full"
                write_json(output / "summary.json", summary)
                if row.get("infrastructure_error") or row.get("cleanup_errors"):
                    break
    except KeyboardInterrupt:
        metadata["failure_type"] = "KeyboardInterrupt"
        raise
    except Exception as exc:
        metadata["failure_type"] = type(exc).__name__
        print(f"Experiment failed ({type(exc).__name__}); inspect the output logs.", file=sys.stderr)
    finally:
        summary = finalize_experiment(None, output, metadata, rows)
    return 0 if summary["complete"] else 1


def main():
    def terminate(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, terminate)
    parser = argparse.ArgumentParser(description="Controlled backend architecture experiment")
    parser.add_argument("--profile", choices=["smoke", "full"], required=True)
    parser.add_argument("--output-root", type=Path, default=Path("/kaggle/working/phase2-results"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validation-only", action="store_true")
    parser.add_argument("--small-data", action="store_true")
    parser.add_argument("--limit-runs", type=int)
    args = parser.parse_args()
    if args.dry_run:
        print(json.dumps([r.to_dict() for r in build_matrix(args.profile)], indent=2))
        return
    raise SystemExit(execute(args))


if __name__ == "__main__":
    main()
