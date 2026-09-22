from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.infrastructure.database.session import create_session_factory
from benchmark.config import BenchmarkConfig
from benchmark.dataset import reset_benchmark_data


def reset_from_config(config: BenchmarkConfig) -> dict[str, int]:
    session_factory = create_session_factory(config.database_url)
    with session_factory() as session:
        return reset_benchmark_data(session)


def main() -> None:
    config = BenchmarkConfig.from_env()
    print(json.dumps(reset_from_config(config), indent=2))


if __name__ == "__main__":
    main()
