from app.benchmark import evaluate


def test_evaluator_counts_detection():

    metrics = evaluate(
        ground_truth_case_ids={
            "CASE_001",
            "CASE_002",
            "CASE_003",
        },
        predicted_exception_case_ids={
            "CASE_001",
            "CASE_003",
        },
        total_cases=10,
    )

    assert metrics.total_cases == 10
    assert metrics.corrupted_cases == 3
    assert metrics.detected_cases == 2
    assert metrics.missed_cases == 1
    assert metrics.false_positive_cases == 0


def test_detection_rate():

    metrics = evaluate(
        ground_truth_case_ids={
            "CASE_001",
            "CASE_002",
            "CASE_003",
            "CASE_004",
        },
        predicted_exception_case_ids={
            "CASE_001",
            "CASE_002",
        },
        total_cases=10,
    )

    assert metrics.detection_rate == 0.5


def test_false_positive():

    metrics = evaluate(
        ground_truth_case_ids={
            "CASE_001",
        },
        predicted_exception_case_ids={
            "CASE_001",
            "CASE_999",
        },
        total_cases=10,
    )

    assert metrics.detected_cases == 1
    assert metrics.false_positive_cases == 1
    assert metrics.precision == 0.5