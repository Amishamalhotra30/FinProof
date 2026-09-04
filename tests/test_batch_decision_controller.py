from decimal import Decimal

import pytest

from app.decisions.batch_controller import (
    BatchDecisionController,
)
from app.decisions.models import (
    BatchControlStatus,
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResult,
    MaterialityLevel,
)


def make_decision(
    case_id: str,
    outcome: DecisionOutcome,
    impact: Decimal = Decimal("0"),
):
    return DecisionResult(
        case_id=case_id,
        decision=outcome,
        reason_code=(
            DecisionReasonCode.ALL_CONTROLS_PASSED
        ),
        basis=["test"],
        financial_impact=impact,
        materiality=MaterialityLevel.NONE,
        policy_rule_id="TEST",
        evidence_sufficient=True,
        investigation_validated=True,
        contradictory_evidence=False,
        supporting_evidence_ids=[],
    )


def test_all_auto_resolved_batch_is_ready_to_close():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE-2",
            DecisionOutcome.AUTO_RESOLVED,
        ),
    ]

    result = BatchDecisionController().evaluate(
        "BATCH-1",
        decisions,
    )

    assert result.total_cases == 2
    assert result.auto_resolved == 2
    assert result.pending == 0
    assert result.human_review == 0
    assert result.blocked == 0

    assert result.final_control_status == (
        BatchControlStatus.READY_TO_CLOSE
    )


def test_pending_case_produces_non_material_exception():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE-2",
            DecisionOutcome.PENDING,
            Decimal("500"),
        ),
    ]

    result = BatchDecisionController().evaluate(
        "BATCH-1",
        decisions,
    )

    assert result.auto_resolved == 1
    assert result.pending == 1

    assert result.final_control_status == (
        BatchControlStatus
        .READY_WITH_NON_MATERIAL_EXCEPTIONS
    )


def test_human_review_requires_batch_review():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE-2",
            DecisionOutcome.HUMAN_REVIEW,
            Decimal("5000"),
        ),
    ]

    result = BatchDecisionController().evaluate(
        "BATCH-1",
        decisions,
    )

    assert result.human_review == 1

    assert result.final_control_status == (
        BatchControlStatus.REVIEW_REQUIRED
    )


def test_resolved_with_approval_requires_batch_review():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.RESOLVED_WITH_APPROVAL,
            Decimal("5000"),
        ),
    ]

    result = BatchDecisionController().evaluate(
        "BATCH-1",
        decisions,
    )

    assert result.human_review == 1

    assert result.final_control_status == (
        BatchControlStatus.REVIEW_REQUIRED
    )


def test_blocked_case_blocks_entire_batch():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE-2",
            DecisionOutcome.BLOCKED,
            Decimal("50000"),
        ),
    ]

    result = BatchDecisionController().evaluate(
        "BATCH-1",
        decisions,
    )

    assert result.blocked == 1

    assert result.final_control_status == (
        BatchControlStatus.BLOCKED
    )


def test_blocked_has_priority_over_human_review():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.HUMAN_REVIEW,
            Decimal("1000"),
        ),
        make_decision(
            "CASE-2",
            DecisionOutcome.BLOCKED,
            Decimal("5000"),
        ),
    ]

    result = BatchDecisionController().evaluate(
        "BATCH-1",
        decisions,
    )

    assert result.human_review == 1
    assert result.blocked == 1

    assert result.final_control_status == (
        BatchControlStatus.BLOCKED
    )


def test_unresolved_financial_value_excludes_auto_resolved():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.AUTO_RESOLVED,
            Decimal("1000"),
        ),
        make_decision(
            "CASE-2",
            DecisionOutcome.HUMAN_REVIEW,
            Decimal("2500"),
        ),
        make_decision(
            "CASE-3",
            DecisionOutcome.PENDING,
            Decimal("500"),
        ),
    ]

    result = BatchDecisionController().evaluate(
        "BATCH-1",
        decisions,
    )

    assert result.unresolved_financial_value == (
        Decimal("3000")
    )


def test_empty_batch_is_ready_to_close():
    result = BatchDecisionController().evaluate(
        "EMPTY-BATCH",
        [],
    )

    assert result.total_cases == 0
    assert result.auto_resolved == 0
    assert result.final_control_status == (
        BatchControlStatus.READY_TO_CLOSE
    )


def test_duplicate_case_decisions_are_rejected():
    decisions = [
        make_decision(
            "CASE-1",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE-1",
            DecisionOutcome.BLOCKED,
        ),
    ]

    with pytest.raises(ValueError):
        BatchDecisionController().evaluate(
            "BATCH-1",
            decisions,
        )