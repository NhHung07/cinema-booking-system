import ast
import json
from pathlib import Path
import tarfile
import tempfile
import unittest


NOTEBOOK = Path(__file__).resolve().parents[2] / "experiments/phase2/kaggle_cpu.ipynb"


class NotebookSourceTests(unittest.TestCase):
    def setUp(self):
        notebook = json.loads(NOTEBOOK.read_text())
        cell = next(c for c in notebook["cells"] if c["cell_type"] == "code")
        tree = ast.parse("".join(cell["source"]))
        # Load the actual notebook's functions without starting a Kaggle session.
        tree.body = [node for node in tree.body
                     if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef))]
        namespace = {}
        exec(compile(tree, str(NOTEBOOK), "exec"), namespace)
        self.assertTrue("prepare_source" in namespace,
                        "Notebook must handle both archives and extracted Dataset source")
        self.prepare = namespace["prepare_source"]
        self.temp = tempfile.TemporaryDirectory(prefix="cinema-notebook-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.inputs = self.base / "input"
        self.inputs.mkdir()
        self.working = self.base / "working"

    def make_source(self, root):
        for name in ["app/main.py", "alembic.ini", "requirements.txt",
                     "experiments/phase2/bootstrap.py", "experiments/phase2/requirements.lock.txt"]:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# source fixture\n")

    def test_extracted_dataset_is_copied_to_writable_working_directory(self):
        original = self.inputs / "datasets/owner/cinema/1/cinema-phase2-source"
        self.make_source(original)
        repo = self.prepare(self.inputs, self.working)
        self.assertTrue(repo.is_relative_to(self.working))
        self.assertEqual((repo / "app/main.py").read_text(), "# source fixture\n")
        (repo / "app/main.py").write_text("changed")
        self.assertEqual((original / "app/main.py").read_text(), "# source fixture\n")

    def test_compressed_dataset_is_extracted_and_can_be_prepared_again(self):
        original = self.base / "source"
        self.make_source(original)
        archive = self.inputs / "cinema-phase2-source.tar.gz"
        with tarfile.open(archive, "w:gz") as output:
            for path in original.rglob("*"):
                if path.is_file():
                    output.add(path, arcname=str(path.relative_to(original)))
        repo = self.prepare(self.inputs, self.working)
        self.assertTrue((repo / "app/main.py").is_file())
        self.assertEqual(self.prepare(self.inputs, self.working), repo)

    def test_multiple_extracted_sources_are_rejected_with_paths(self):
        for name in ["dataset-one", "dataset-two"]:
            self.make_source(self.inputs / name)
        with self.assertRaisesRegex(RuntimeError, "dataset-one"):
            self.prepare(self.inputs, self.working)

    def test_missing_source_has_actionable_error(self):
        with self.assertRaisesRegex(RuntimeError, "Add Input"):
            self.prepare(self.inputs, self.working)

    def test_extracted_dataset_without_wrapper_directory_is_supported(self):
        self.make_source(self.inputs / "cinema")
        repo = self.prepare(self.inputs, self.working)
        self.assertTrue((repo / "experiments/phase2/bootstrap.py").is_file())

    def test_invalid_archive_does_not_leave_a_partial_repository(self):
        incomplete = self.base / "main.py"
        incomplete.write_text("# missing source files\n")
        with tarfile.open(self.inputs / "cinema-phase2-source.tar.gz", "w:gz") as output:
            output.add(incomplete, arcname="app/main.py")
        with self.assertRaisesRegex(RuntimeError, "backend"):
            self.prepare(self.inputs, self.working)
        self.assertEqual(list(self.working.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
