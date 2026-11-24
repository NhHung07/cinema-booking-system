from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class BundleTests(unittest.TestCase):
    def test_bundle_works_without_site_packages_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory(prefix="cinema-bundle-") as directory:
            output = Path(directory) / "cinema-phase2-source.tar.gz"
            command = [sys.executable, "-S", "-B", "-m", "experiments.phase2.bundle",
                       "--output", str(output)]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            with tarfile.open(output) as archive:
                names = archive.getnames()
                self.assertIn("app/main.py", names)
                self.assertIn("experiments/phase2/kaggle_cpu.ipynb", names)
                self.assertIn("docs/phase2-evaluation.md", names)
                self.assertFalse(any(name.startswith((".env", ".venv/", "frontend/"))
                                     for name in names))
            original = output.read_bytes()
            repeated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
