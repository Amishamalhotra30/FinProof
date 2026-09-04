from app.evaluation.performance import (
    PerformanceBenchmark,
    PerformanceMeasurement,
    measure_performance,
)


def test_performance_measurement_calculates_throughput():
    measurement = PerformanceMeasurement(
        cases=100,
        records=500,
        generation_seconds=1.0,
        reconciliation_seconds=2.0,
    )

    assert (
        measurement.generation_cases_per_second
        == 100.0
    )

    assert (
        measurement.reconciliation_cases_per_second
        == 50.0
    )

    assert (
        measurement.reconciliation_records_per_second
        == 250.0
    )


def test_zero_generation_time_returns_infinity():
    measurement = PerformanceMeasurement(
        cases=100,
        records=500,
        generation_seconds=0.0,
        reconciliation_seconds=1.0,
    )

    assert (
        measurement.generation_cases_per_second
        == float("inf")
    )


def test_zero_reconciliation_time_returns_infinity():
    measurement = PerformanceMeasurement(
        cases=100,
        records=500,
        generation_seconds=1.0,
        reconciliation_seconds=0.0,
    )

    assert (
        measurement.reconciliation_cases_per_second
        == float("inf")
    )

    assert (
        measurement.reconciliation_records_per_second
        == float("inf")
    )


def test_empty_performance_benchmark():
    benchmark = PerformanceBenchmark(
        measurements=()
    )

    assert benchmark.largest_case_count == 0
    assert (
        benchmark.minimum_reconciliation_throughput
        == 0.0
    )


def test_performance_benchmark_tracks_largest_workload():
    benchmark = PerformanceBenchmark(
        measurements=(
            PerformanceMeasurement(
                cases=100,
                records=500,
                generation_seconds=0.1,
                reconciliation_seconds=0.1,
            ),
            PerformanceMeasurement(
                cases=1000,
                records=5000,
                generation_seconds=0.5,
                reconciliation_seconds=0.5,
            ),
        )
    )

    assert benchmark.largest_case_count == 1000


def test_performance_rejects_non_positive_case_count():
    try:
        measure_performance(
            case_counts=(0,),
        )
    except ValueError as exc:
        assert "positive" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )