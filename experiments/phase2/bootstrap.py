"""Chuẩn bị dependency trong Kaggle; không cài dịch vụ lên máy phát triển."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.request


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def install_services():
    if not Path("/kaggle/working").is_dir() or os.geteuid() != 0 or not shutil.which("apt-get"):
        raise RuntimeError("Service installation requires a root Kaggle Debian/Ubuntu notebook")
    release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
    codename = release.get("VERSION_CODENAME", "").strip('"')
    if not re.fullmatch(r"[a-z]+", codename):
        raise RuntimeError("Cannot determine Debian/Ubuntu codename")
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    policy = Path("/usr/sbin/policy-rc.d")
    original = policy.read_bytes() if policy.exists() else None
    mode = policy.stat().st_mode if policy.exists() else None
    try:
        # Prevent package post-install scripts from starting unmanaged services.
        policy.write_text("#!/bin/sh\nexit 101\n")
        policy.chmod(0o755)
        run(["apt-get", "update", "-qq"], env=env)
        run(["apt-get", "install", "-y", "ca-certificates", "gnupg"], env=env)
        pg_key = Path("/usr/share/keyrings/phase2-postgresql.asc")
        pg_key.write_bytes(urllib.request.urlopen("https://www.postgresql.org/media/keys/ACCC4CF8.asc", timeout=30).read())
        Path("/etc/apt/sources.list.d/phase2-pgdg.list").write_text(
            f"deb [signed-by={pg_key}] https://apt.postgresql.org/pub/repos/apt {codename}-pgdg main\n")
        redis_key = urllib.request.urlopen("https://packages.redis.io/gpg", timeout=30).read()
        subprocess.run(["gpg", "--batch", "--yes", "--dearmor", "-o", "/usr/share/keyrings/phase2-redis.gpg"],
                       input=redis_key, check=True)
        Path("/etc/apt/sources.list.d/phase2-redis.list").write_text(
            f"deb [signed-by=/usr/share/keyrings/phase2-redis.gpg] https://packages.redis.io/deb {codename} main\n")
        run(["apt-get", "update", "-qq"], env=env)
        versions = subprocess.check_output(["apt-cache", "madison", "redis-server"], text=True)
        redis_version = next((line.split("|")[1].strip() for line in versions.splitlines()
                              if re.match(r"^(?:\d+:)?7\.", line.split("|")[1].strip())), None)
        if redis_version is None:
            raise RuntimeError("No Redis 7 package available for this notebook image")
        run(["apt-get", "install", "-y", "--allow-downgrades", "postgresql-16", "postgresql-client-16",
             f"redis-server={redis_version}", f"redis-tools={redis_version}"], env=env)
    finally:
        if original is None:
            policy.unlink(missing_ok=True)
        else:
            policy.write_bytes(original)
            policy.chmod(mode)


def main():
    parser = argparse.ArgumentParser(description="Install the locked Python environment and local services on Kaggle")
    parser.add_argument("--install", action="store_true", help="Explicitly prepare the Kaggle environment")
    args = parser.parse_args()
    if not args.install:
        parser.error("Pass --install to prepare a Kaggle CPU notebook")
    if not Path("/kaggle/working").is_dir():
        raise RuntimeError("This installer is restricted to Kaggle")
    root = Path(__file__).resolve().parents[2]
    uv = shutil.which("uv")
    if not uv:
        run([sys.executable, "-m", "pip", "install", "uv"])
        uv = shutil.which("uv")
    venv = Path("/kaggle/working/phase2-venv")
    if not venv.exists():
        run([uv, "venv", "--python", "3.12", str(venv)])
    run([uv, "pip", "sync", "--python", str(venv / "bin/python"), "--require-hashes",
         "-r", str(root / "experiments/phase2/requirements.lock.txt")])
    install_services()
    print(f"Prepared Python: {venv / 'bin/python'}")


if __name__ == "__main__":
    main()
