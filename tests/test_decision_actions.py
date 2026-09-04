from decimal import Decimal

import pytest

from app.decisions.actions import (
    DecisionActionExecutor,
    InvalidDecisionAction,
)
from app.decisions.models import (
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResult,
    MaterialityLevel,
    ReviewAction,
)


def make_decision(
    decision: DecisionOutcome,
    reason_code: DecisionReasonCode,
    **overrides,
) -> DecisionResult:
    values = {
        "case_id": "CASE_ACTION_TEST",
        "decision": decision,
        "reason_code": reason_code,
        "basis": ["Test decision basis."],
        "financial_impact": Decimal("500"),
        "materiality": MaterialityLevel.MEDIUM,
        "policy_rule_id": "P7-TEST",
        "evidence_sufficient": True,
        "investigation_validated": True,
        "contradictory_evidence": False,
        "supporting_evidence_ids": ["EV-001"],
    }

    values.update(overrides)

    return DecisionResult(**values)


def test_auto_resolved_creates_mark_resolved_action():
    decision = make_decision(
        DecisionOutcome.AUTO_RESOLVED,
        DecisionReasonCode.ALL_CONTROLS_PASSED,
    )

    action = DecisionActionExecutor().execute(
        decision
    )

    assert action.case_id == "CASE_ACTION_TEST"
    assert action.action_type == "MARK_RESOLVED"


def test_pending_creates_mark_pending_action():
    decision = make_decision(
        DecisionOutcome.PENDING,
        DecisionReasonCode.EXPECTED_EVENT_PENDING,
    )

    action = DecisionActionExecutor().execute(
        decision
    )

    assert action.action_type == "MARK_PENDING"


def test_human_review_creates_review_action():
    decision = make_decision(
        DecisionOutcome.HUMAN_REVIEW,
        DecisionReasonCode.INSUFFICIENT_EVIDENCE,
    )

    action = DecisionActionExecutor().execute(
        decision
    )

    assert action.action_type == "CREATE_HUMAN_REVIEW"


def test_resolved_with_approval_creates_review_action():
    decision = make_decision(
        DecisionOutcome.RESOLVED_WITH_APPROVAL,
        DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL,
    )

    action = DecisionActionExecutor().execute(
        decision
    )

    assert action.action_type == "CREATE_HUMAN_REVIEW"


def test_blocked_creates_block_action():
    decision = make_decision(
        DecisionOutcome.BLOCKED,
        DecisionReasonCode.MATERIAL_UNRESOLVED,
    )

    action = DecisionActionExecutor().execute(
        decision
    )

    assert action.action_type == "BLOCK_CASE"


def test_review_package_contains_evidence_references():
    decision = make_decision(
        DecisionOutcome.HUMAN_REVIEW,
        DecisionReasonCode.INSUFFICIENT_EVIDENCE,
        supporting_evidence_ids=[
            "EV-001",
            "EV-002",
        ],
    )

    package = (
        DecisionActionExecutor()
        .create_review_package(decision)
    )

    assert package.case_id == "CASE_ACTION_TEST"
    assert package.evidence_ids == [
        "EV-001",
        "EV-002",
    ]


def test_review_package_accepts_investigation_context():
    decision = make_decision(
        DecisionOutcome.HUMAN_REVIEW,
        DecisionReasonCode.UNRESOLVED_DISCREPANCY,
    )

    package = (
        DecisionActionExecutor()
        .create_review_package(
            decision,
            discrepancy_id="DISC-001",
            control_id="SETTLEMENT_AMOUNT",
            investigation_status="UNRESOLVED",
            investigation_summary="Partial evidence found.",
            investigation_conclusion="Unable to fully explain.",
            evidence_ids=["EV-001"],
        )
    )

    assert package.discrepancy_id == "DISC-001"
    assert package.control_id == "SETTLEMENT_AMOUNT"
    assert package.investigation_status == "UNRESOLVED"
    assert package.evidence_ids == ["EV-001"]


def test_review_package_rejects_auto_resolved_case():
    decision = make_decision(
        DecisionOutcome.AUTO_RESOLVED,
        DecisionReasonCode.ALL_CONTROLS_PASSED,
    )

    with pytest.raises(InvalidDecisionAction):
        DecisionActionExecutor().create_review_package(
            decision
        )


def test_human_approval_record_is_created():
    decision = make_decision(
        DecisionOutcome.RESOLVED_WITH_APPROVAL,
        DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL,
    )

    record = (
        DecisionActionExecutor()
        .record_review(
            decision,
            ReviewAction.APPROVE,
            "Evidence reviewed and approved.",
            reviewer_id="REVIEWER-001",
        )
    )

    assert record.case_id == "CASE_ACTION_TEST"
    assert record.action == ReviewAction.APPROVE
    assert record.comment == (
        "Evidence reviewed and approved."
    )
    assert record.reviewer_id == "REVIEWER-001"
    assert record.previous_decision == (
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )
    assert record.human_override is True


def test_rejection_is_recorded():
    decision = make_decision(
        DecisionOutcome.HUMAN_REVIEW,
        DecisionReasonCode.INSUFFICIENT_EVIDENCE,
    )

    record = (
        DecisionActionExecutor()
        .record_review(
            decision,
            ReviewAction.REJECT,
            "Evidence is not sufficient.",
        )
    )

    assert record.action == ReviewAction.REJECT


def test_more_evidence_request_is_recorded():
    decision = make_decision(
        DecisionOutcome.HUMAN_REVIEW,
        DecisionReasonCode.INSUFFICIENT_EVIDENCE,
    )

    record = (
        DecisionActionExecutor()
        .record_review(
            decision,
            ReviewAction.REQUEST_MORE_EVIDENCE,
            "Need bank statement evidence.",
        )
    )

    assert record.action == (
        ReviewAction.REQUEST_MORE_EVIDENCE
    )


def test_empty_review_comment_is_rejected():
    decision = make_decision(
        DecisionOutcome.HUMAN_REVIEW,
        DecisionReasonCode.INSUFFICIENT_EVIDENCE,
    )

    with pytest.raises(InvalidDecisionAction):
        DecisionActionExecutor().record_review(
            decision,
            ReviewAction.APPROVE,
            "   ",
        )


def test_review_action_not_allowed_for_auto_resolved_case():
    decision = make_decision(
        DecisionOutcome.AUTO_RESOLVED,
        DecisionReasonCode.ALL_CONTROLS_PASSED,
    )

    with pytest.raises(InvalidDecisionAction):
        DecisionActionExecutor().record_review(
            decision,
            ReviewAction.APPROVE,
            "Approved.",
        )


def test_action_executor_does_not_change_financial_amount():
    decision = make_decision(
        DecisionOutcome.AUTO_RESOLVED,
        DecisionReasonCode.FULLY_EXPLAINED_NON_MATERIAL,
        financial_impact=Decimal("750"),
    )

    action = DecisionActionExecutor().execute(
        decision
    )

    assert action.case_id == decision.case_id
    assert decision.financial_impact == Decimal("750")