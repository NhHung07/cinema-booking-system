import csv
import json
from pathlib import Path
import threading
import time

import psutil
import psycopg
from prometheus_client.parser import text_string_to_metric_families


def metric_delta(before: str, after: str) -> dict:
    def values(document):
        return {(sample.name, tuple(sorted(sample.labels.items()))): sample.value
                for family in text_string_to_metric_families(document) for sample in family.samples
                if not sample.name.endswith("_created")}
    first, last = values(before), values(after)
    def total(name, **labels):
        return sum(value - first.get((metric, tags), 0) for (metric, tags), value in last.items()
                   if metric == name and all(dict(tags).get(k) == v for k, v in labels.items()))
    queries = total("cinema_sql_queries_total")
    requests = total("cinema_http_requests_total")
    hits = total("cinema_cache_operations_total", outcome="hit")
    misses = total("cinema_cache_operations_total", outcome="miss")
    errors = total("cinema_cache_operations_total", outcome="error")
    write_errors = total("cinema_cache_operations_total", outcome="write_error")
    return {"sql_queries": queries, "observed_http_requests": requests,
            "sql_per_request": queries / requests if requests else None,
            "cache_hits": hits, "cache_misses": misses, "cache_errors": errors + write_errors,
            "cache_write_errors": write_errors,
            "cache_hit_ratio": hits / (hits + misses + errors) if hits + misses + errors else None,
            "pool_timeouts": total("cinema_db_pool_timeouts_total"),
            "worker_pids": sorted({dict(tags)["pid"] for (name, tags), value in last.items()
                                   if name == "cinema_worker_requests_total" and value > 0})}


class ResourceSampler:
    def __init__(self, roots: dict[str, int | None], database_url: str, output: Path):
        self.roots, self.database_url, self.output = roots, database_url, output
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.samples, self.errors, self.processes = [], [], {}
        self.missing_at_stop = []

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopped.set()
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            self.errors.append("sampler_did_not_stop")
        for component, root in self.roots.items():
            if component == "load" or root is None:
                continue
            try:
                process = psutil.Process(root)
                if not process.is_running() or process.status() in {psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD}:
                    self.missing_at_stop.append(component)
            except psutil.NoSuchProcess:
                self.missing_at_stop.append(component)

    def _run(self):
        connection = None
        try:
            connection = psycopg.connect(self.database_url, connect_timeout=2,
                                         application_name="phase2_sampler", options="-c statement_timeout=1000", autocommit=True)
            with self.output.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["monotonic", "component", "cpu_percent", "rss_bytes", "process_count", "process_ids", "wait_events"])
                writer.writeheader()
                while not self.stopped.is_set():
                    stamp = time.perf_counter()
                    for component, root in self.roots.items():
                        if root is None:
                            continue
                        cpu, rss, count, pids = 0., 0, 0, []
                        try:
                            family = [psutil.Process(root)] + psutil.Process(root).children(recursive=True)
                        except psutil.NoSuchProcess:
                            family = []
                        for process in family:
                            try:
                                # Reuse Process objects: cpu_percent is relative to the previous sample.
                                process = self.processes.setdefault(process.pid, process)
                                cpu += process.cpu_percent()
                                rss += process.memory_info().rss
                                count += 1
                                pids.append(process.pid)
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                pass
                        waits = {}
                        if component == "postgres":
                            waits = dict(connection.execute("SELECT coalesce(wait_event_type,'running'),count(*) FROM pg_stat_activity WHERE datname=current_database() AND application_name!='phase2_sampler' AND state='active' GROUP BY 1").fetchall())
                        row = {"monotonic": stamp, "component": component, "cpu_percent": cpu,
                               "rss_bytes": rss, "process_count": count, "process_ids": sorted(pids), "wait_events": json.dumps(waits)}
                        writer.writerow(row)
                        self.samples.append(row)
                    stream.flush()
                    self.stopped.wait(1)
        except Exception as exc:
            # Do not persist connection strings or exception messages containing secrets.
            self.errors.append(type(exc).__name__)
        finally:
            if connection is not None:
                connection.close()

    def summary(self, start: float, end: float) -> dict:
        samples = [s for s in self.samples if start <= s["monotonic"] < end]
        load = [s["cpu_percent"] for s in samples if s["component"] == "load"]
        result = {"errors": self.errors, "generator_saturated": bool(load) and sum(v >= 90 for v in load) / len(load) >= .2}
        api_sets = {tuple(s["process_ids"]) for s in samples if s["component"] == "api"}
        result["api_process_changed"] = len(api_sets) > 1 or () in api_sets
        # Include warm-up and drain; a healthy measurement interval cannot erase a service failure.
        missing = set(self.missing_at_stop)
        for sample in self.samples:
            component = sample["component"]
            root = self.roots.get(component)
            if component != "load" and root is not None and root not in sample["process_ids"]:
                missing.add(component)
        result["required_service_missing"] = sorted(missing)
        previous = set()
        for sample in self.samples:
            if sample["component"] == "api":
                current = set(sample["process_ids"])
                if previous - current:
                    result["api_process_changed"] = True
                previous = current
        for component in self.roots:
            rows = [s for s in samples if s["component"] == component]
            result[component] = {"observed": bool(rows),
                                 "cpu_mean_percent": sum(r["cpu_percent"] for r in rows) / len(rows) if rows else None,
                                 "rss_sampled_peak_bytes": max((r["rss_bytes"] for r in rows), default=None)}
        return result
