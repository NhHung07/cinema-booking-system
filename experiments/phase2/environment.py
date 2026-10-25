import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

import psutil


def _read(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def inspect_environment() -> dict:
    affinity = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else list(range(os.cpu_count() or 1))
    quota = _read("/sys/fs/cgroup/cpu.max")
    effective = float(len(affinity))
    if quota and quota.split()[0] != "max":
        amount, period = map(int, quota.split())
        effective = min(effective, amount / period)
    memory = psutil.virtual_memory().available
    limit, current = _read("/sys/fs/cgroup/memory.max"), _read("/sys/fs/cgroup/memory.current")
    if limit and limit != "max" and current:
        memory = min(memory, int(limit) - int(current))
    distributions = sorted((d.metadata["Name"], d.version) for d in importlib.metadata.distributions())
    packages = [f"{name}=={version}" for name, version in distributions]
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        diff = subprocess.check_output(["git", "diff", "--binary"])
    except (OSError, subprocess.CalledProcessError):
        commit, diff = "unavailable", b""
    return {"python": platform.python_version(), "platform": platform.platform(),
            "cpu_model": next((line.split(':', 1)[1].strip() for line in (_read('/proc/cpuinfo') or '').splitlines() if line.startswith('model name')), platform.processor()),
            "cpu_affinity": affinity, "cpu_quota": quota, "effective_cpus": effective,
            "memory_available_bytes": memory, "packages": packages,
            "kaggle_runtime": bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")) and Path("/kaggle/working").is_dir(),
            "disk_available_bytes": shutil.disk_usage(Path.cwd()).free,
            "packages_sha256": hashlib.sha256('\n'.join(packages).encode()).hexdigest(),
            "commit": commit, "tracked_diff_sha256": hashlib.sha256(diff).hexdigest()}


def preflight(environment: dict, validation_only: bool = False) -> None:
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use Python 3.12 for a reproducible experiment")
    if not validation_only and (environment["effective_cpus"] < 4 or environment["memory_available_bytes"] < 8 * 1024**3):
        raise RuntimeError("Canonical experiment requires at least 4 effective CPUs and 8 GiB available RAM")
    if not validation_only and not environment["kaggle_runtime"]:
        raise RuntimeError("Canonical results must be measured in a Kaggle notebook; use --validation-only for local checks")
    if environment["disk_available_bytes"] < 4 * 1024**3:
        raise RuntimeError("At least 4 GiB free disk is required")


def write_json(path: Path, data) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
