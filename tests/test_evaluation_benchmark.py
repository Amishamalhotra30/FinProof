from app.evaluation.benchmark_adapter import (
    build_benchmark_ground_truth,
    generate_evaluation_benchmark,
)


def test_benchmark_ground_truth_is_evaluation_only():
    benchmark, ground_truth = (
        generate_evaluation_benchmark(
            num_cases=30,
            seed=42,
        )
    )

    assert len(ground_truth.cases) == 30

    benchmark_case_ids = {
        case.case_id
        for case in benchmark.ground_truth.cases
    }

    ground_truth_case_ids = {
        case.case_id
        for case in ground_truth.cases
    }

    assert (
        benchmark_case_ids
        == ground_truth_case_ids
    )
    
def test_corrupted_cases_are_marked_as_failures():
    benchmark, ground_truth = (
        generate_evaluation_benchmark(
            num_cases=100,
            seed=42,
        )
    )

    corrupted_case_ids = {
        event.case_id
        for event in benchmark.corruption_events
    }

    expected_failure_ids = {
        case.case_id
        for case in ground_truth.cases
        if case.expected_failure
    }

    assert (
        corrupted_case_ids
        == expected_failure_ids
    )


def test_corruption_maps_to_expected_controls():
    benchmark, ground_truth = (
        generate_evaluation_benchmark(
            num_cases=100,
            seed=42,
        )
    )

    expected_by_case = (
        ground_truth.by_case_id()
    )

    for event in benchmark.corruption_events:
        expected = expected_by_case[
            event.case_id
        ]

        assert (
            event.corruption_type.value
            in expected.expected_corruption_types
        )


def test_material_corruptions_are_marked():
    benchmark, ground_truth = (
        generate_evaluation_benchmark(
            num_cases=100,
            seed=42,
        )
    )

    expected_by_case = (
        ground_truth.by_case_id()
    )

    for event in benchmark.corruption_events:
        if event.corruption_type.value in {
            "MISSING_RECORD",
            "AMOUNT_MISMATCH",
            "REFERENCE_MISMATCH",
            "TIMING_ANOMALY",
        }:
            assert (
                expected_by_case[
                    event.case_id
                ].expected_material_failure
            )


def test_same_seed_produces_same_ground_truth():
    benchmark_a, truth_a = (
        generate_evaluation_benchmark(
            num_cases=100,
            seed=42,
        )
    )

    benchmark_b, truth_b = (
        generate_evaluation_benchmark(
            num_cases=100,
            seed=42,
        )
    )

    assert truth_a == truth_b

    assert (
        benchmark_a.corruption_events
        == benchmark_b.corruption_events
    )


def test_different_seed_changes_benchmark():
    _, truth_a = generate_evaluation_benchmark(
        num_cases=100,
        seed=42,
    )

    _, truth_b = generate_evaluation_benchmark(
        num_cases=100,
        seed=43,
    )

    assert truth_a != truth_b