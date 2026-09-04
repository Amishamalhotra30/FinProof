from decimal import Decimal

from app.decisions.models import (
    DecisionOutcome,
    DecisionPolicy,
)
from app.decisions.service import DecisionService
from app.decisions.metrics import (
    DecisionMetricsCalculator,
)


def test_phase7_benchmark_contains_100_cases():
    from scripts.run_phase7_evaluation import (
        _build_benchmark_cases,
    )

    cases = _build_benchmark_cases()

    assert len(cases) == 100


def test_phase7_benchmark_expected_outcome_distribution():
    from scripts.run_phase7_evaluation import (
        _build_benchmark_cases,
    )

    cases = _build_benchmark_cases()

    expected = [
        outcome
        for _, _, outcome in cases
    ]

    assert expected.count(
        DecisionOutcome.AUTO_RESOLVED
    ) == 60

    assert expected.count(
        DecisionOutcome.PENDING
    ) == 10

    assert expected.count(
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    ) == 10

    assert expected.count(
        DecisionOutcome.HUMAN_REVIEW
    ) == 15

    assert expected.count(
        DecisionOutcome.BLOCKED
    ) == 5


def test_phase7_benchmark_has_zero_false_resolutions():
    from scripts.run_phase7_evaluation import (
        _build_benchmark_cases,
    )

    cases = _build_benchmark_cases()

    service = DecisionService(
        policy=DecisionPolicy(
            auto_resolution_threshold=Decimal("1000")
        )
    )

    decisions = []
    ground_truth = {}

    for verification, investigation, expected in cases:
        result = service.decide(
            verification,
            investigation,
        )

        decisions.append(result.decision)
        ground_truth[
            verification.case_id
        ] = expected

    metrics = DecisionMetricsCalculator().calculate(
        decisions,
        ground_truth=ground_truth,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.total_cases == 100
    assert metrics.false_resolutions == 0
    assert metrics.false_resolution_rate == Decimal("0")