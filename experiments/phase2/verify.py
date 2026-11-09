from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from experiments.phase2.runner import ROOT, check_redis
from experiments.phase2.runtime import Processes, local_postgres, start_redis


def main():
    with tempfile.TemporaryDirectory(prefix="cinema-phase2-verify-") as temporary, ExitStack() as stack:
        directory = Path(temporary)
        admin = os.environ.get("PHASE2_ADMIN_URL")
        if not admin:
            admin, _ = stack.enter_context(local_postgres(directory))
        processes = Processes()
        stack.callback(processes.close)
        redis_url = os.environ.get("PHASE2_REDIS_URL")
        if not redis_url:
            redis_url, _ = start_redis(processes, directory)
        check_redis(redis_url)
        env = dict(os.environ, PHASE2_ADMIN_URL=admin, PHASE2_REDIS_URL=redis_url)
        result = subprocess.run([sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider"], cwd=ROOT, env=env)
        if result.returncode:
            # Preserve diagnostic logs without copying any environment secrets.
            for name in ["postgres.log", "initdb.log", "redis.log"]:
                log = directory / name
                if log.exists():
                    print(log.read_text()[-3000:], file=sys.stderr)
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
