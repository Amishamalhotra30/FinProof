from dataclasses import dataclass

from app.benchmark import (
    BenchmarkMetrics,
    CorruptionTypeMetrics,
    evaluate,
    evaluate_by_corruption_type,
    generate_benchmark,
)
from app.reconciliation.controller import (
    reconcile_records,
)
from app.reconciliation.models import (
    MatchStatus,
)


@dataclass(frozen=True)
class BenchmarkReport:
    metrics: BenchmarkMetrics
    corruption_metrics: list[CorruptionTypeMetrics]
    detected_cases: set[str]
    missed_cases: set[str]
    false_positive_cases: set[str]


def _run_reconciliation(
    num_cases: int,
    seed: int,
):
    benchmark = generate_benchmark(
        num_cases=num_cases,
        seed=seed,
    )

    results = reconcile_records(
        benchmark.observed_records
    )

    ground_truth_case_ids = {
        event.case_id
        for event in benchmark.corruption_events
    }

    predicted_exception_case_ids = {
        result.case_id.removesuffix("_PAYMENT")
        for result in results
        if result.status == MatchStatus.EXCEPTION
    }

    return (
        benchmark,
        ground_truth_case_ids,
        predicted_exception_case_ids,
    )


def run_benchmark(
    num_cases: int = 100,
    seed: int = 42,
) -> BenchmarkMetrics:

    report = run_detailed_benchmark(
        num_cases=num_cases,
        seed=seed,
    )

    return report.metrics


def run_detailed_benchmark(
    num_cases: int = 100,
    seed: int = 42,
) -> BenchmarkReport:

    (
        benchmark,
        ground_truth_case_ids,
        predicted_exception_case_ids,
    ) = _run_reconciliation(
        num_cases=num_cases,
        seed=seed,
    )

    metrics = evaluate(
        ground_truth_case_ids=ground_truth_case_ids,
        predicted_exception_case_ids=(
            predicted_exception_case_ids
        ),
        total_cases=num_cases,
    )

    corruption_metrics = (
        evaluate_by_corruption_type(
            corruption_events=(
                benchmark.corruption_events
            ),
            predicted_exception_case_ids=(
                predicted_exception_case_ids
            ),
        )
    )

    detected_cases = (
        ground_truth_case_ids
        & predicted_exception_case_ids
    )

    missed_cases = (
        ground_truth_case_ids
        - predicted_exception_case_ids
    )

    false_positive_cases = (
        predicted_exception_case_ids
        - ground_truth_case_ids
    )

    return BenchmarkReport(
        metrics=metrics,
        corruption_metrics=corruption_metrics,
        detected_cases=detected_cases,
        missed_cases=missed_cases,
        false_positive_cases=false_positive_cases,
    )