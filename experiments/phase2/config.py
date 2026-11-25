from dataclasses import asdict, dataclass
import random

SEED = 20261025
VARIANTS = {"A": (1, False), "B": (1, True), "C": (2, False), "D": (2, True)}
BOOKING_VARIANTS = {"D0": (False, 0), "D1": (True, 0), "D2": (True, 4), "D-limit": (False, 4)}
BOOKING_USER_PERIOD_SECONDS = 0.1
BOOKING_CLIENT_TIMEOUT_SECONDS = 5.0
SCENARIOS = ("R1", "R2", "R3", "R4")
PROFILES = ("smoke", "full", "booking-diagnostic", "booking-smoke", "booking-followup")


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


def build_matrix(profile: str, *, include_split_auth: bool = True) -> list[RunSpec]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    booking = profile.startswith("booking-")
    smoke = profile in {"smoke", "booking-smoke"}
    diagnostic = profile == "booking-diagnostic"
    names = (("D0",) if diagnostic else
             ("D0", "D1", "D2") if include_split_auth else ("D0", "D-limit")) if booking else tuple(VARIANTS)
    loads = [10] if smoke else [50, 100] if diagnostic else [10, 50, 100]
    rng = random.Random(SEED)
    runs = []
    for scenario in (SCENARIOS[1:] if booking else SCENARIOS):
        for users in loads:
            for repeat in range(1, (1 if smoke or diagnostic else 3) + 1):
                variants = list(names)
                rng.shuffle(variants)
                for variant in variants:
                    runs.append(RunSpec(variant, scenario, users, repeat,
                                        5 if smoke else 15,
                                        10 if smoke else 45))
    return runs


def variant_runtime(variant: str) -> tuple[int, bool]:
    return VARIANTS["D"] if variant in BOOKING_VARIANTS else VARIANTS[variant]


def variant_environment(variant: str, namespace: str) -> dict[str, str]:
    workers, cache = variant_runtime(variant)
    split_auth, limit = BOOKING_VARIANTS.get(variant, (False, 0))
    return {
        "DB_POOL_SIZE": str(8 // workers), "DB_MAX_OVERFLOW": "0",
        "DB_POOL_TIMEOUT": "3", "CATALOG_CACHE_ENABLED": str(cache).lower(),
        "BOOKING_SPLIT_AUTH": str(split_auth).lower(),
        "BOOKING_MAX_IN_FLIGHT_PER_WORKER": str(limit),
        "CATALOG_CACHE_NAMESPACE": namespace, "CATALOG_CACHE_TTL": "120",
        "REDIS_TIMEOUT": "0.1", "METRICS_ENABLED": "true",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "720",
    }
