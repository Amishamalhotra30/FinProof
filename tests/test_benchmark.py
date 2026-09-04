from app.benchmark import generate_benchmark


def test_generate_benchmark():
    benchmark = generate_benchmark(
        num_cases=100,
        seed=42,
    )

    assert len(benchmark.ground_truth.cases) == 100

    assert len(benchmark.clean_records["orders"]) == 100
    assert len(benchmark.clean_records["payments"]) == 100

    assert len(benchmark.corruption_events) == 30
def test_benchmark_observed_records_differ_from_clean():
    benchmark = generate_benchmark(
        num_cases=100,
        seed=42,
    )

    assert (
        benchmark.observed_records
        != benchmark.clean_records
    )
def test_benchmark_ground_truth_is_preserved():
    benchmark_a = generate_benchmark(
        num_cases=100,
        seed=42,
    )

    benchmark_b = generate_benchmark(
        num_cases=100,
        seed=42,
    )

    assert (
        benchmark_a.ground_truth
        == benchmark_b.ground_truth
    )

    assert (
        benchmark_a.corruption_events
        == benchmark_b.corruption_events
    )