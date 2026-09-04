from app.benchmark_runner import (
    run_detailed_benchmark,
)


def test_detailed_benchmark_runs():

    report = run_detailed_benchmark(
        num_cases=100,
        seed=42,
    )

    assert report.metrics.total_cases == 100

    assert report.metrics.corrupted_cases > 0

    assert len(report.corruption_metrics) > 0

    for metric in report.corruption_metrics:
        assert metric.injected > 0
        assert metric.detected >= 0
        assert metric.missed >= 0
        assert 0.0 <= metric.detection_rate <= 1.0


def test_detailed_benchmark_is_deterministic():

    first = run_detailed_benchmark(
        num_cases=100,
        seed=42,
    )

    second = run_detailed_benchmark(
        num_cases=100,
        seed=42,
    )

    assert first == second