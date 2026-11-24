"""Source selection shared by packaging and experiment capture (stdlib only)."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def source_files() -> list[Path]:
    files = []
    for name in ["app", "migrations", "experiments", "tests", "scripts", "requirements.txt", "alembic.ini", "pytest.ini"]:
        path = ROOT / name
        files.extend([p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"] if path.is_dir() else [path])
    return sorted(files)
