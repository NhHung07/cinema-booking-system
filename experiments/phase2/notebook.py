"""Điều phối subprocess từ notebook, chuyển tiếp thao tác ngắt tới runner."""
import os
from pathlib import Path
import signal
import subprocess


def run_checked(command: list[str], cwd: Path | None = None) -> None:
    process = subprocess.Popen(command, cwd=cwd, start_new_session=True)
    try:
        code = process.wait()
    except KeyboardInterrupt:
        for sig, timeout in [(signal.SIGINT, 60), (signal.SIGTERM, 15), (signal.SIGKILL, 5)]:
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                break
            try:
                process.wait(timeout=timeout)
                break
            except subprocess.TimeoutExpired:
                continue
        raise
    if code:
        raise subprocess.CalledProcessError(code, command)
