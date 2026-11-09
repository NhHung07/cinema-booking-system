import argparse
import csv
import json
import os
from pathlib import Path
import statistics
import tempfile

from experiments.phase2.environment import write_json
from experiments.phase2.results import aggregate_runs


def flatten(row: dict) -> dict:
    result = {key: row.get(key) for key in ["variant", "scenario", "users", "repeat", "valid", "completed_rps",
              "successful_booking_rps", "unexpected_failure_ratio", "infrastructure_error", "waves_per_second"]}
    result.update({key: row.get("server_metrics", {}).get(key) for key in
                   ["sql_per_request", "sql_queries", "cache_hit_ratio", "cache_errors", "pool_timeouts"]})
    for component in ["api", "postgres", "redis", "load"]:
        data = row.get("resources", {}).get(component, {})
        for field in ["cpu_mean_percent", "rss_sampled_peak_bytes"]:
            result[f"{component}_{field}"] = data.get(field)
    for group, data in row.get("groups", {}).items():
        for field in ["count", "p50_ms", "p95_ms", "p99_ms"]:
            result[f"{group}_{field}"] = data.get(field)
    return result


def _csv(path: Path, rows: list[dict]):
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["variant", "scenario", "users"]
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate_report(root: Path) -> dict:
    metadata = json.loads((root / "experiment.json").read_text())
    rows = [json.loads(path.read_text()) for path in sorted(root.glob("[0-9]*/result.json"))]
    expected = metadata["matrix"]
    summary = aggregate_runs(rows, len(expected), expected_matrix=expected)
    summary["complete"] = summary["complete"] and not metadata.get("cleanup_errors") and not metadata.get("failure_type")
    primary = summary["complete"] and metadata["canonical"] and metadata["profile"] == "full" and len(expected) == 144
    summary.update(canonical=metadata["canonical"], profile=metadata["profile"], primary_complete=primary)
    write_json(root / "summary.json", summary)
    _csv(root / "runs.csv", [flatten(row) for row in rows])
    _csv(root / "summary.csv", [{k: v for k, v in group.items() if k != "latencies"} for group in summary["groups"]])

    # Explicit writable cache avoids touching the user's home from a Kaggle worker.
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "cinema-phase2-matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    label = "Thí nghiệm Kaggle CPU" if metadata["canonical"] else "Kiểm tra cục bộ — không dùng kết luận Pha 2"
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    for scenario, axis in zip(["R1", "R2", "R3", "R4"], axes.flat):
        for variant in "ABCD":
            groups = sorted((g for g in summary["groups"] if g["scenario"] == scenario and g["variant"] == variant), key=lambda g: g["users"])
            if groups:
                axis.errorbar([g["users"] for g in groups], [g["completed_rps_median"] for g in groups],
                              yerr=[[g["completed_rps_median"] - g["completed_rps_min"] for g in groups],
                                    [g["completed_rps_max"] - g["completed_rps_median"] for g in groups]],
                              marker="o", capsize=3, label=variant)
        axis.set(title=scenario + (" — gồm phản hồi 409" if scenario == "R3" else ""), xlabel="Người dùng đồng thời", ylabel="Phản hồi hoàn thành / giây")
        axis.grid(alpha=.25)
        if axis.lines:
            axis.legend()
    figure.suptitle(label)
    figure.tight_layout()
    figure.savefig(root / "throughput.png", dpi=180)
    figure.savefig(root / "throughput.svg")
    plt.close(figure)

    latency, axes = plt.subplots(2, 2, figsize=(12, 8))
    target_groups = {"R1": ["read:200"], "R2": ["write:201"], "R3": ["conflict:201", "conflict:409"], "R4": ["read:200", "write:201"]}
    for scenario, axis in zip(target_groups, axes.flat):
        for variant in "ABCD":
            for name in target_groups[scenario]:
                groups = sorted((g for g in summary["groups"] if g["scenario"] == scenario and g["variant"] == variant and name in g["latencies"]), key=lambda g: g["users"])
                if groups:
                    axis.plot([g["users"] for g in groups], [g["latencies"][name]["p95_median_ms"] for g in groups], marker="o", label=f"{variant} {name}")
        axis.set(title=scenario, xlabel="Người dùng đồng thời", ylabel="Median p95 qua các lần lặp (ms)")
        axis.grid(alpha=.25)
        if axis.lines:
            axis.legend(fontsize=7)
    latency.suptitle(label)
    latency.tight_layout()
    latency.savefig(root / "latency.png", dpi=180)
    latency.savefig(root / "latency.svg")
    plt.close(latency)

    resources, axes = plt.subplots(2, 1, figsize=(13, 7))
    # Global elapsed time keeps every run visible, including invalid runs.
    origin = None
    colors = {"api": "tab:blue", "postgres": "tab:orange", "redis": "tab:green", "load": "tab:red"}
    observed_components = set()
    for directory in sorted(root.glob("[0-9]*")):
        path = directory / "resources.csv"
        if not path.is_file():
            continue
        with path.open() as stream:
            samples = list(csv.DictReader(stream))
        for component in ["api", "postgres", "redis", "load"]:
            selected = [r for r in samples if r["component"] == component]
            if not selected:
                continue
            observed_components.add(component)
            if origin is None:
                origin = float(selected[0]["monotonic"])
            elapsed = [float(r["monotonic"]) - origin for r in selected]
            axes[0].plot(elapsed, [float(r["cpu_percent"]) for r in selected], color=colors[component], linewidth=.8)
            axes[1].plot(elapsed, [int(r["rss_bytes"]) / 1024**2 for r in selected], color=colors[component], linewidth=.8)
    if observed_components:
        from matplotlib.lines import Line2D
        axes[0].legend(handles=[Line2D([0], [0], color=colors[c], label=c) for c in colors if c in observed_components])
    axes[0].set(ylabel="CPU (% một lõi logic)")
    axes[1].set(xlabel="Thời gian toàn thí nghiệm (giây)", ylabel="Tổng RSS lấy mẫu (MiB)")
    for axis in axes:
        axis.grid(alpha=.25)
    resources.suptitle(label + " — tài nguyên theo thời gian, gồm cả lượt lỗi")
    resources.tight_layout()
    resources.savefig(root / "resources.png", dpi=180)
    resources.savefig(root / "resources.svg")
    plt.close(resources)

    comparisons = []
    index = {(g["variant"], g["scenario"], g["users"]): g for g in summary["groups"]}
    for scenario in ["R1", "R2", "R3", "R4"]:
        for users in sorted({g["users"] for g in summary["groups"]}):
            for after, before in [("B", "A"), ("C", "A"), ("D", "C"), ("D", "B"), ("D", "A")]:
                left, right = index.get((after, scenario, users)), index.get((before, scenario, users))
                if left and right and right["completed_rps_median"]:
                    comparisons.append({"scenario": scenario, "users": users, "comparison": f"{after}/{before}",
                                        "rps_change_percent": (left["completed_rps_median"] / right["completed_rps_median"] - 1) * 100,
                                        "after_repeats": left["repeats"], "before_repeats": right["repeats"]})
    _csv(root / "comparisons.csv", comparisons)

    lines = ["# Đánh giá kiến trúc backend", "", f"Nguồn: {label}.", "",
             "Trạng thái Pha 2: " + ("đủ ma trận đo chính." if primary else "**chưa hoàn tất thí nghiệm Kaggle chính**."), "",
             f"Lượt quan sát: {len(rows)}/{len(expected)}; hợp lệ: {summary['valid_runs']}; không hợp lệ: {summary['invalid_runs']}.", "",
             "## Kiến trúc và phương pháp", "",
             "A: một worker, không cache. B: một worker và Redis cache-aside. C: hai worker, không cache. D: hai worker và Redis. Tổng ngân sách pool API là tám kết nối trong mọi biến thể.", "",
             "Phép đo dùng cùng snapshot dữ liệu và cấu hình môi trường. R1 đọc danh mục; R2 đặt ghế khác nhau; R3 tranh cùng ghế theo vòng; R4 kết hợp đọc và ghi. Mỗi kết quả được giữ cùng spec, metrics và log gốc.", "",
             "## Kết quả hợp lệ", "", "| Biến thể | Kịch bản | Người dùng | Số lần | RPS median | Min–max |", "|---|---|---:|---:|---:|---|" ]
    for group in summary["groups"]:
        lines.append(f"| {group['variant']} | {group['scenario']} | {group['users']} | {group['repeats']} | {group['completed_rps_median']:.2f} | {group['completed_rps_min']:.2f}–{group['completed_rps_max']:.2f} |")
    lines.extend(["", "## Lượt không hợp lệ", ""])
    for row in rows:
        if not row.get("valid"):
            lines.append(f"- {row['variant']}/{row['scenario']}/{row['users']}/lần {row['repeat']}: lỗi hạ tầng={row.get('infrastructure_error') or 'không'}; lỗi workload={row.get('errors', [])}; tài nguyên={json.dumps(row.get('resources', {}), ensure_ascii=False)}.")
    if not summary["invalid_runs"]:
        lines.append("Không ghi nhận lượt không hợp lệ trong phần đã chạy.")
    lines.extend(["", "## Cách đọc và giới hạn", "",
                  "- RPS của R3 bao gồm 409; số vé thành công nằm riêng trong successful_booking_rps. Tính đúng đắn được đối chiếu với database sau mỗi lượt.",
                  "- p95/p99 phân theo nhóm kết quả trong runs.csv; không lấy trung bình percentile của worker. comparisons.csv chứa thay đổi throughput của các cặp kiến trúc, chưa phải kết luận ý nghĩa thống kê.",
                  "- SQL/request và cache hit ratio lấy từ chênh lệch metrics sau warm-up đến hết drain; cửa sổ này có thể dài hơn cửa sổ throughput 45 giây để hoàn tất vòng tranh chấp.",
                  "- CPU phần trăm tính theo một CPU logic; RSS là tổng RSS tiến trình và có thể tính lặp vùng nhớ dùng chung. Đỉnh bộ nhớ là giá trị lấy mẫu mỗi giây.",
                  "- Thiếu quan sát PostgreSQL/Redis trong kiểm tra dịch vụ ngoài được để trống, không thay bằng số 0. Các lượt không hợp lệ vẫn có trong runs.csv và không được dùng vẽ so sánh.",
                  "- Dữ liệu danh mục cache có thể cũ tối đa 120 giây; các dữ liệu ghế và đơn vé không cache. Redis hỏng được fallback về PostgreSQL.",
                  "- Số người dùng của Locust là concurrency, không phải RPS đặt trước. Chưa bão hòa ở mức tải cao nhất không chứng minh công suất tối đa.",
                  "- Kết quả trên một máy không chứng minh khả năng chịu lỗi nhiều máy hoặc tính sẵn sàng cao. Kết quả kiểm tra cục bộ không thay thế phép đo Kaggle CPU.", ""])
    (root / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()
    summary = generate_report(args.output_root)
    print(json.dumps({key: summary[key] for key in ["valid_runs", "invalid_runs", "primary_complete"]}))


if __name__ == "__main__":
    main()
