import json

from experiments.phase2.report import generate_report
from experiments.phase2.results import aggregate_runs


def test_duplicate_run_cannot_complete_an_expected_matrix():
    expected = [{"variant": v, "scenario": "R1", "users": 10, "repeat": 1} for v in ["A", "B"]]
    rows = [dict(expected[0], valid=True, completed_rps=20)] * 2
    summary = aggregate_runs(rows, expected=2, expected_matrix=expected)
    assert summary["complete"] is False
    assert summary["matrix_matches"] is False


def test_report_keeps_failed_runs_and_cannot_present_local_smoke_as_phase2_results(tmp_path):
    experiment = {"profile": "smoke", "canonical": False, "matrix": [
        {"variant": "A", "scenario": "R1", "users": 10, "repeat": 1},
        {"variant": "B", "scenario": "R1", "users": 10, "repeat": 1}]}
    (tmp_path / "experiment.json").write_text(json.dumps(experiment))
    for index, variant, valid, rps in [(1, "A", True, 10), (2, "B", False, 9999)]:
        directory = tmp_path / f"{index:03}"
        directory.mkdir()
        (directory / "result.json").write_text(json.dumps(dict(experiment["matrix"][index-1], valid=valid, completed_rps=rps)))
    generate_report(tmp_path)
    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["primary_complete"] is False
    assert summary["invalid_runs"] == 1
    assert "9999" in (tmp_path / "runs.csv").read_text()
    report = (tmp_path / "report.md").read_text()
    assert "kiểm tra cục bộ" in report.lower()
    assert "chưa hoàn tất" in report.lower()
    assert (tmp_path / "throughput.png").is_file()
    assert (tmp_path / "throughput.svg").is_file()
    assert (tmp_path / "resources.png").is_file()
    assert (tmp_path / "resources.svg").is_file()
