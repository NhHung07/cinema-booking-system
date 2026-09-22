from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.infrastructure.database.session import create_session_factory
from benchmark.config import BenchmarkConfig
from benchmark.dataset import DatasetSpec, seed_benchmark_data, write_dataset


def seed_from_config(config: BenchmarkConfig) -> dict[str, object]:
    session_factory = create_session_factory(config.database_url)
    with session_factory() as session:
        metadata = seed_benchmark_data(session, DatasetSpec(random_seed=config.random_seed))
    write_dataset(metadata, config.dataset_file)
    return metadata


def main() -> None:
    config = BenchmarkConfig.from_env()
    metadata = seed_from_config(config)
    print(json.dumps({"dataset_file": str(config.dataset_file), **metadata["counts"]}, indent=2))


if __name__ == "__main__":
    main()
