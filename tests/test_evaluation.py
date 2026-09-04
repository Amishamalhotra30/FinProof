from decimal import Decimal

from app.evaluation.dataset import (
    build_dataset,
)
from app.evaluation.ground_truth import (
    build_ground_truth,
)
from app.evaluation.models import (
    EvaluationSplit,
)
from app.evaluation.runner import (
    EvaluationRunner,
)


class FakeVerification:
    def __init__(
        self,
        status,
        discrepancies=None,
    ):
        self.status = status
        self.discrepancies = (
            discrepancies or []
        )


class FakeDiscrepancy:
    def __init__(
        self,
        materiality="NONE",
    ):
        self.materiality = materiality


class FakeDecision:
    def __init__(
        self,
        decision,
    ):
        self.decision = decision


def test_dataset_is_deterministic():
    first = build_dataset(
        smoke_cases=2,
        standard_cases=3,
        stress_cases=1,
        held_out_cases=1,
        seed=42,
    )

    second = build_dataset(
        smoke_cases=2,
        standard_cases=3,
        stress_cases=1,
        held_out_cases=1,
        seed=42,
    )

    assert first == second


def test_dataset_contains_all_splits():
    dataset = build_dataset(
        smoke_cases=2,
        standard_cases=3,
        stress_cases=4,
        held_out_cases=5,
    )

    assert (
        len(
            dataset.cases_for_split(
                EvaluationSplit.SMOKE
            )
        )
        == 2
    )

    assert (
        len(
            dataset.cases_for_split(
                EvaluationSplit.STANDARD
            )
        )
        == 3
    )

    assert (
        len(
            dataset.cases_for_split(
                EvaluationSplit.STRESS
            )
        )
        == 4
    )

    assert (
        len(
            dataset.cases_for_split(
                EvaluationSplit.HELD_OUT
            )
        )
        == 5
    )


def test_evaluation_detects_failure():
    dataset = build_dataset(
        smoke_cases=1,
        standard_cases=0,
        stress_cases=0,
        held_out_cases=0,
    )

    case_id = dataset.cases[0].case_id

    ground_truth = build_ground_truth(
        dataset.cases,
        expected_failure_case_ids={
            case_id
        },
    )

    actual_results = {
        case_id: FakeVerification(
            status="FAILED",
            discrepancies=[
                FakeDiscrepancy()
            ],
        )
    }

    result = EvaluationRunner().evaluate(
        dataset,
        ground_truth,
        actual_results,
    )

    summary = result.summary_for(
        EvaluationSplit.SMOKE
    )

    assert summary is not None
    assert summary.expected_failures == 1
    assert summary.detected_failures == 1
    assert summary.false_passes == 0
    assert summary.false_fails == 0


def test_evaluation_detects_false_pass():
    dataset = build_dataset(
        smoke_cases=1,
        standard_cases=0,
        stress_cases=0,
        held_out_cases=0,
    )

    case_id = dataset.cases[0].case_id

    ground_truth = build_ground_truth(
        dataset.cases,
        expected_failure_case_ids={
            case_id
        },
    )

    actual_results = {
        case_id: FakeVerification(
            status="VERIFIED"
        )
    }

    result = EvaluationRunner().evaluate(
        dataset,
        ground_truth,
        actual_results,
    )

    summary = result.summary_for(
        EvaluationSplit.SMOKE
    )

    assert summary is not None
    assert summary.false_passes == 1
    assert summary.false_pass_rate == Decimal("1")


def test_evaluation_detects_false_fail():
    dataset = build_dataset(
        smoke_cases=1,
        standard_cases=0,
        stress_cases=0,
        held_out_cases=0,
    )

    case_id = dataset.cases[0].case_id

    ground_truth = build_ground_truth(
        dataset.cases
    )

    actual_results = {
        case_id: FakeVerification(
            status="FAILED",
            discrepancies=[
                FakeDiscrepancy()
            ],
        )
    }

    result = EvaluationRunner().evaluate(
        dataset,
        ground_truth,
        actual_results,
    )

    summary = result.summary_for(
        EvaluationSplit.SMOKE
    )

    assert summary is not None
    assert summary.false_fails == 1
    assert summary.false_fail_rate == Decimal("1")


def test_material_failure_is_detected():
    dataset = build_dataset(
        smoke_cases=1,
        standard_cases=0,
        stress_cases=0,
        held_out_cases=0,
    )

    case_id = dataset.cases[0].case_id

    ground_truth = build_ground_truth(
        dataset.cases,
        expected_failure_case_ids={
            case_id
        },
        expected_material_failure_case_ids={
            case_id
        },
    )

    actual_results = {
        case_id: FakeVerification(
            status="FAILED",
            discrepancies=[
                FakeDiscrepancy(
                    materiality="HIGH"
                )
            ],
        )
    }

    result = EvaluationRunner().evaluate(
        dataset,
        ground_truth,
        actual_results,
    )

    evaluation = result.cases[0]

    assert evaluation.expected_material_failure
    assert evaluation.detected_material_failure


def test_decision_accuracy_is_evaluated():
    dataset = build_dataset(
        smoke_cases=1,
        standard_cases=0,
        stress_cases=0,
        held_out_cases=0,
    )

    case_id = dataset.cases[0].case_id

    ground_truth = build_ground_truth(
        dataset.cases,
        expected_decisions={
            case_id: "AUTO_RESOLVED"
        },
    )

    actual_results = {
        case_id: FakeDecision(
            "AUTO_RESOLVED"
        )
    }

    result = EvaluationRunner().evaluate(
        dataset,
        ground_truth,
        actual_results,
    )

    evaluation = result.cases[0]

    assert evaluation.decision_correct