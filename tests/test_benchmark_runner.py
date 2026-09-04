from app.benchmark_runner import (
    run_benchmark,
)


def test_real_benchmark_runs():

    metrics = run_benchmark(
        num_cases=100,
        seed=42,
    )

    assert metrics.total_cases == 100

    assert metrics.corrupted_cases > 0

    assert metrics.detected_cases >= 0

    assert metrics.missed_cases >= 0

    assert metrics.false_positive_cases >= 0


def test_real_benchmark_is_deterministic():

    first = run_benchmark(
        num_cases=100,
        seed=42,
    )

    second = run_benchmark(
        num_cases=100,
        seed=42,
    )

    assert first == second