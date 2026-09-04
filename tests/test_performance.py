from app.benchmark import generate_benchmark
from app.performance import (
    measure_throughput,
)


def test_throughput_measurement():

    benchmark = generate_benchmark(
        num_cases=100,
        seed=42,
    )

    metrics = measure_throughput(
        benchmark.observed_records,
        cases=100,
    )

    assert metrics.cases == 100
    assert metrics.records > 0
    assert metrics.elapsed_seconds >= 0
    assert metrics.cases_per_second > 0
    assert metrics.records_per_second > 0