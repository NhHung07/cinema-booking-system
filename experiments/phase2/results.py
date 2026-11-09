from collections import Counter, defaultdict
import math
from statistics import median


def percentile(histogram: Counter, quantile: float) -> float | None:
    if not histogram:
        return None
    target = math.ceil(sum(histogram.values()) * quantile)
    seen = 0
    for value, count in sorted(histogram.items()):
        seen += count
        if seen >= target:
            return value
    raise AssertionError("Invalid histogram")


class RequestLedger:
    def __init__(self, start: float, end: float):
        self.start, self.end = start, end
        self.histograms = defaultdict(Counter)
        self.completed = self.bookings = self.failures = self.requests = 0

    def record(self, kind: str, started: float, finished: float, status: int, elapsed_ms: float, expected: int):
        if not self.start <= started < self.end:
            return
        self.requests += 1
        # R3 accepts one 201 and the remaining 409; correctness is checked per wave.
        good = status == expected or (kind == "conflict" and status in {201, 409})
        self.failures += not good
        self.histograms[f"{kind}:{status}"][round(elapsed_ms, 1)] += 1
        if finished < self.end:
            self.completed += 1
            self.bookings += kind in {"write", "conflict"} and status == 201

    def summary(self) -> dict:
        duration = self.end - self.start
        groups = {name: {"count": sum(h.values()), "p50_ms": percentile(h, .5),
                         "p95_ms": percentile(h, .95), "p99_ms": percentile(h, .99)}
                  for name, h in sorted(self.histograms.items())}
        return {"requests": self.requests, "completed_rps": self.completed / duration,
                "successful_booking_rps": self.bookings / duration,
                "unexpected_failures": self.failures,
                "unexpected_failure_ratio": self.failures / self.requests if self.requests else None,
                "groups": groups}


def aggregate_runs(rows: list[dict], expected: int, expected_matrix: list[dict] | None = None) -> dict:
    groups = defaultdict(list)
    for row in rows:
        if row.get("valid"):
            groups[(row["variant"], row["scenario"], row["users"])].append(row)
    summaries = []
    for (variant, scenario, users), runs in sorted(groups.items()):
        summary = {"variant": variant, "scenario": scenario, "users": users, "repeats": len(runs)}
        for metric in ["completed_rps", "successful_booking_rps", "unexpected_failure_ratio"]:
            values = [r[metric] for r in runs if r.get(metric) is not None]
            if values:
                summary.update({f"{metric}_median": median(values), f"{metric}_min": min(values), f"{metric}_max": max(values)})
        # Per-run percentiles stay separate; never average worker percentiles.
        summary["latencies"] = {name: {"p95_median_ms": median(v), "p95_min_ms": min(v), "p95_max_ms": max(v)}
                                for name in sorted({k for r in runs for k in r.get("groups", {})})
                                if (v := [r["groups"][name]["p95_ms"] for r in runs if name in r.get("groups", {})])}
        summaries.append(summary)
    valid = sum(bool(r.get("valid")) for r in rows)
    identity = lambda row: (row["variant"], row["scenario"], row["users"], row.get("repeat"))
    matches = expected_matrix is None or Counter(map(identity, rows)) == Counter(map(identity, expected_matrix))
    return {"expected_runs": expected, "observed_runs": len(rows), "valid_runs": valid,
            "invalid_runs": len(rows) - valid, "complete": len(rows) == expected and valid == expected and matches,
            "matrix_matches": matches,
            "groups": summaries}
