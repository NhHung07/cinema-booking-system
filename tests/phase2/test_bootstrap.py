import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.phase2 import bootstrap


@unittest.skipUnless(shutil.which("uv"), "uv is required for the bootstrap CLI regression")
class BootstrapTests(unittest.TestCase):
    def test_bootstrap_sync_accepts_lockfile_with_real_uv(self):
        with tempfile.TemporaryDirectory(prefix="cinema-bootstrap-") as temporary:
            root = Path(temporary)
            working = root / "working"
            venv = working / "phase2-venv"
            subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)],
                           check=True, capture_output=True)
            module = root / "source/experiments/phase2/bootstrap.py"
            module.parent.mkdir(parents=True)
            (module.parent / "requirements.lock.txt").write_text("# No third-party packages needed\n")

            def local_path(value):
                if str(value).startswith("/kaggle/working"):
                    return working / str(value).removeprefix("/kaggle/working").lstrip("/")
                return Path(value)

            # Only substitute Kaggle paths and APT installation; uv runs for real, offline.
            with patch.object(bootstrap, "__file__", str(module)), \
                 patch.object(bootstrap, "Path", side_effect=local_path), \
                 patch.object(bootstrap, "install_services"), \
                 patch.object(sys, "argv", [str(module), "--install"]), \
                 patch.dict(os.environ, {"UV_CACHE_DIR": str(root / "cache"), "UV_OFFLINE": "1"}), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                bootstrap.main()
            self.assertIn("Prepared Python:", output.getvalue())
            self.assertTrue((venv / "bin/python").is_file())


if __name__ == "__main__":
    unittest.main()
