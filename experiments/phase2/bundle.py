import argparse
import hashlib
from pathlib import Path
import tarfile

from experiments.phase2.runner import ROOT, source_files


def main():
    parser = argparse.ArgumentParser(description="Package backend source for a private Kaggle Dataset")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("Write the bundle outside the source repository")
    with tarfile.open(output, "x:gz") as archive:
        for path in source_files():
            archive.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
        document = ROOT / "docs/phase2-evaluation.md"
        if document.exists():
            archive.add(document, arcname=str(document.relative_to(ROOT)), recursive=False)
    print(f"{output}\nsha256={hashlib.sha256(output.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
