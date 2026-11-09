from contextlib import contextmanager
import os
from pathlib import Path
import pwd
import secrets
import shutil
import signal
import socket
import subprocess
import tempfile
import time
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql
import psutil

from experiments.phase2.safety import validate_admin_url, validate_database_name


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Processes:
    def __init__(self):
        self.children = []

    def start(self, command: list[str], log: Path, env: dict | None = None):
        with log.open("ab") as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                       env=env, start_new_session=True)
        self.children.append(process)
        return process

    def stop(self, process) -> None:
        # The session/group may outlive its original leader (e.g. Uvicorn workers).
        for sig, timeout in [(signal.SIGTERM, 10), (signal.SIGKILL, 5)]:
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            deadline = time.monotonic() + timeout
            while self._group_alive(process.pid) and time.monotonic() < deadline:
                time.sleep(.02)
            if not self._group_alive(process.pid):
                break
        if self._group_alive(process.pid):
            raise RuntimeError(f"Owned process group {process.pid} did not stop")
        process.wait(timeout=1)
        if process in self.children:
            self.children.remove(process)

    @staticmethod
    def _group_alive(group: int) -> bool:
        for item in psutil.process_iter(["pid", "status"]):
            try:
                if item.info["status"] not in {psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD} and os.getpgid(item.pid) == group:
                    return True
            except (ProcessLookupError, PermissionError, psutil.NoSuchProcess):
                continue
        return False

    def close(self):
        errors = []
        for process in list(reversed(self.children)):
            try:
                self.stop(process)
            except Exception as exc:
                errors.append(type(exc).__name__)
        if errors:
            raise RuntimeError("Owned process cleanup failed: " + ",".join(errors))


class DatabaseAdmin:
    def __init__(self, url: str, owner: str):
        self.url = validate_admin_url(url)
        self.owner = owner
        self.owned = set()

    def database_url(self, name: str) -> str:
        validate_database_name(name, self.owner)
        parts = urlsplit(self.url)
        return urlunsplit(parts._replace(path="/" + name))

    def create(self, suffix: str, template: str | None = None) -> str:
        name = validate_database_name(f"cinema_phase2_{self.owner}_{suffix}", self.owner)
        with psycopg.connect(self.url, autocommit=True) as connection:
            if template is not None:
                validate_database_name(template, self.owner)
                if template not in self.owned:
                    raise ValueError("Template is not owned by this experiment")
                connection.execute(sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(sql.Identifier(name), sql.Identifier(template)))
            else:
                connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        self.owned.add(name)
        return name

    def drop(self, name: str):
        validate_database_name(name, self.owner)
        if name not in self.owned:
            raise ValueError("Refusing to drop an unowned database")
        with psycopg.connect(self.url, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        self.owned.remove(name)

    def close(self):
        errors = []
        for name in sorted(self.owned, key=lambda name: name.endswith("snapshot")):
            try:
                self.drop(name)
            except Exception as exc:
                errors.append(type(exc).__name__)
        if errors:
            raise RuntimeError("Owned database cleanup failed: " + ",".join(errors))


def postgres_binary(name: str) -> str:
    candidate = Path("/usr/lib/postgresql/16/bin") / name
    found = str(candidate) if candidate.exists() else shutil.which(name)
    if not found:
        raise RuntimeError("PostgreSQL 16 binaries unavailable; run the Kaggle bootstrap first")
    return found


@contextmanager
def local_postgres(log_directory: Path):
    processes = Processes()
    runtime = Path(tempfile.mkdtemp(prefix="cinema-phase2-pg-"))
    try:
        prefix = []
        if os.geteuid() == 0:
            user = pwd.getpwnam("postgres")
            os.chown(runtime, user.pw_uid, user.pw_gid)
            prefix = ["runuser", "-u", "postgres", "--"]
        password = secrets.token_hex(24)
        pwfile = runtime / "password"
        pwfile.write_text(password)
        pwfile.chmod(0o600)
        if prefix:
            os.chown(pwfile, user.pw_uid, user.pw_gid)
        with (log_directory / "initdb.log").open("wb") as log:
            subprocess.run(prefix + [postgres_binary("initdb"), "-D", str(runtime / "data"), "-U", "phase2",
                                     "--auth-host=scram-sha-256", "--auth-local=trust", "--pwfile=" + str(pwfile)],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        pwfile.unlink()
        port = free_port()
        process = processes.start(prefix + [postgres_binary("postgres"), "-D", str(runtime / "data"),
                                            "-h", "127.0.0.1", "-p", str(port), "-k", str(runtime),
                                            "-c", "max_connections=32", "-c", "shared_buffers=256MB",
                                            "-c", "timezone=UTC", "-c", "fsync=on", "-c", "synchronous_commit=on"],
                                  log_directory / "postgres.log")
        url = f"postgresql://phase2:{password}@127.0.0.1:{port}/postgres"
        deadline = time.monotonic() + 30
        while True:
            try:
                with psycopg.connect(url, connect_timeout=1):
                    break
            except psycopg.Error:
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError("PostgreSQL startup failed; inspect postgres.log") from None
                time.sleep(.1)
        yield url, process.pid
    finally:
        processes.close()
        shutil.rmtree(runtime)


def start_redis(processes: Processes, directory: Path) -> tuple[str, int]:
    executable = shutil.which("redis-server")
    if not executable:
        raise RuntimeError("Redis 7 server unavailable; run the Kaggle bootstrap first")
    port = free_port()
    process = processes.start([executable, "--bind", "127.0.0.1", "--port", str(port), "--save", "",
                               "--appendonly", "no", "--maxmemory", "128mb", "--maxmemory-policy", "allkeys-lru"],
                              directory / "redis.log")
    return f"redis://127.0.0.1:{port}/0", process.pid
