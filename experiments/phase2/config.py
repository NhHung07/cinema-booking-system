from dataclasses import asdict, dataclass
import random

SEED = 20261025
VARIANTS = {"A": (1, False), "B": (1, True), "C": (2, False), "D": (2, True)}
SCENARIOS = ("R1", "R2", "R3", "R4")


@dataclass(frozen=True)
class RunSpec:
    variant: str
    scenario: str
    users: int
    repeat: int
    warmup: int
    duration: int
    drain: int = 10

    def to_dict(self) -> dict:
        return asdict(self)


def build_matrix(profile: str) -> list[RunSpec]:
    if profile not in {"smoke", "full"}:
        raise ValueError("Profile must be smoke or full")
    rng = random.Random(SEED)
    runs = []
    for scenario in SCENARIOS:
        for users in ([10] if profile == "smoke" else [10, 50, 100]):
            for repeat in range(1, (1 if profile == "smoke" else 3) + 1):
                variants = list(VARIANTS)
                rng.shuffle(variants)
                for variant in variants:
                    runs.append(RunSpec(variant, scenario, users, repeat,
                                        5 if profile == "smoke" else 15,
                                        10 if profile == "smoke" else 45))
    return runs


def variant_environment(variant: str, namespace: str) -> dict[str, str]:
    workers, cache = VARIANTS[variant]
    return {
        "DB_POOL_SIZE": str(8 // workers), "DB_MAX_OVERFLOW": "0",
        "DB_POOL_TIMEOUT": "3", "CATALOG_CACHE_ENABLED": str(cache).lower(),
        "CATALOG_CACHE_NAMESPACE": namespace, "CATALOG_CACHE_TTL": "120",
        "REDIS_TIMEOUT": "0.1", "METRICS_ENABLED": "true",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "720",
    }
