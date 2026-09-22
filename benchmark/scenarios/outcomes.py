def classify_concurrent_status(status_code: int) -> str:
    if status_code == 201:
        return "created"
    if status_code == 409:
        return "expected_conflict"
    return "unexpected_failure"
