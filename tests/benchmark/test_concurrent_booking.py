from benchmark.scenarios.outcomes import classify_concurrent_status


def test_expected_conflict_is_not_a_technical_failure() -> None:
    assert classify_concurrent_status(201) == "created"
    assert classify_concurrent_status(409) == "expected_conflict"
    assert classify_concurrent_status(400) == "unexpected_failure"
    assert classify_concurrent_status(500) == "unexpected_failure"
