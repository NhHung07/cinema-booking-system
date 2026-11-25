from collections import Counter, defaultdict
import math
from statistics import median

from experiments.phase2.config import build_matrix


def booking_overloaded(kind: str, status: int, payload) -> bool:
    return (kind in {"write", "conflict"} and status == 503
            and isinstance(payload, dict) and payload.get("code") == "booking_overloaded")


def classify_wave(statuses: dict, users: int) -> str:
    winners = statuses.get(201, 0)
    if winners > 1:
        return "multiple_winners"
    if sum(statuses.values()) != users or set(statuses) - {201, 409, "booking_overloaded"}:
        return "unexpected"
    return "winner" if winners else "no_winner"


def summarize_waves(waves: list[dict], start: float, end: float) -> dict:
    measured = [wave for wave in waves if start <= wave["started"] and wave["finished"] < end]
    outcomes = Counter(wave["outcome"] for wave in measured)
    winners = sum(wave["statuses"].get(201, 0) == 1 for wave in measured)
    without_success = sum(not wave["statuses"].get(201, 0) for wave in measured)
    return {"completed_waves": len(measured), "waves_per_second": len(measured) / (end - start),
            "winning_waves_per_second": winners / (end - start),
            "no_winner_wave_ratio": without_success / len(measured) if measured else None,
            "unexpected_waves": outcomes["unexpected"], "wave_outcomes": dict(outcomes)}


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
        self.booking_responses = self.booking_rejections = self.client_timeouts = 0
        self.statuses = Counter()

    def record(self, kind: str, started: float, finished: float, status: int, elapsed_ms: float,
               expected: int, *, overloaded: bool = False, timed_out: bool = False):
        if not self.start <= started < self.end:
            return
        self.requests += 1
        # R3 accepts one 201 and the remaining 409; correctness is checked per wave.
        good = status == expected or (kind == "conflict" and status in {201, 409})
        self.failures += not good and not overloaded
        self.booking_rejections += overloaded
        self.booking_responses += kind in {"write", "conflict"} and status == 201
        self.statuses[status] += 1
        self.client_timeouts += timed_out
        group = f"{kind}:{status}" + (":booking_overloaded" if overloaded else "")
        self.histograms[group][round(elapsed_ms, 1)] += 1
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
                "booking_rejections": self.booking_rejections,
                "booking_rejection_ratio": self.booking_rejections / self.requests if self.requests else None,
                "failure_including_rejections_ratio": (self.failures + self.booking_rejections) / self.requests if self.requests else None,
                "successful_booking_ratio": self.booking_responses / self.requests if self.requests else None,
                "client_timeouts": self.client_timeouts, "no_http_response": self.statuses[0],
                "http_500": self.statuses[500],
                "other_503": self.statuses[503] - self.booking_rejections,
                "groups": groups}


def aggregate_runs(rows: list[dict], expected: int, expected_matrix: list[dict] | None = None) -> dict:
    groups = defaultdict(list)
    for row in rows:
        if row.get("valid"):
            groups[(row["variant"], row["scenario"], row["users"])].append(row)
    summaries = []
    for (variant, scenario, users), runs in sorted(groups.items()):
        summary = {"variant": variant, "scenario": scenario, "users": users, "repeats": len(runs)}
        for metric in ["completed_rps", "successful_booking_rps", "unexpected_failure_ratio",
                       "booking_rejection_ratio", "failure_including_rejections_ratio",
                       "successful_booking_ratio", "no_http_response", "client_timeouts", "http_500", "other_503",
                       "winning_waves_per_second", "no_winner_wave_ratio", "unexpected_waves"]:
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


def experiment_summary(metadata: dict, rows: list[dict]) -> dict:
    matrix = metadata["matrix"]
    profile, canonical = metadata["profile"], metadata["canonical"]
    errors = metadata.get("cleanup_errors", [])
    summary = aggregate_runs(rows, len(matrix), expected_matrix=matrix)
    complete = bool(summary["complete"] and not errors and not metadata.get("failure_type"))
    followup_expected = []
    if profile == "booking-followup":
        followup_expected = [r.to_dict() for r in build_matrix(profile, include_split_auth=len(matrix) == 81)]
    summary.update(complete=complete, canonical=canonical, profile=profile, cleanup_errors=errors,
                   primary_complete=complete and canonical and profile == "full" and len(matrix) == 144,
                   booking_followup_complete=complete and canonical and bool(followup_expected)
                   and matrix == followup_expected)
    return summary
