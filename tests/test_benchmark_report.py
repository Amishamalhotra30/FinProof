from app.benchmark_runner import (
    run_detailed_benchmark,
)


def test_benchmark_report_contains_case_lists():

    report = run_detailed_benchmark(
        num_cases=100,
        seed=42,
    )

    assert report.metrics.total_cases == 100

    assert (
        len(report.detected_cases)
        + len(report.missed_cases)
        == report.metrics.corrupted_cases
    )

    assert (
        len(report.false_positive_cases)
        == report.metrics.false_positive_cases
    )


def test_benchmark_report_is_deterministic():

    first = run_detailed_benchmark(
        num_cases=100,
        seed=42,
    )

    second = run_detailed_benchmark(
        num_cases=100,
        seed=42,
    )

    assert first == second