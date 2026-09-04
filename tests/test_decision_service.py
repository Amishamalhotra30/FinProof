from decimal import Decimal

import pytest

from app.decisions.models import (
    CaseState,
    DecisionOutcome,
    DecisionReasonCode,
    MaterialityLevel,
    ReviewAction,
)
from app.decisions.service import (
    DecisionService,
)
from app.investigation.models import (
    InvestigationResult,
    InvestigationStatus,
)
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Discrepancy,
    ExpectedFinancialState,
    Materiality,
    VerificationResult,
    VerificationStatus,
)


def make_verification(
    *,
    status=VerificationStatus.FAILED,
    discrepancy=True,
    difference=Decimal("500"),
    materiality=Materiality.LOW,
    blocking=False,
):
    discrepancies = []

    if discrepancy:
        discrepancies.append(
            Discrepancy(
                discrepancy_id="DISC-SERVICE",
                control_id="SETTLEMENT_AMOUNT",
                expected_value=Decimal("1000"),
                observed_value=(
                    Decimal("1000")
                    + difference
                ),
                difference=difference,
                materiality=materiality,
                blocking=blocking,
            )
        )

    controls = []

    if status == VerificationStatus.VERIFIED:
        controls.append(
            ControlCheck(
                control_id="SETTLEMENT_AMOUNT",
                control_name="Settlement amount",
                status=ControlStatus.PASS,
            )
        )

    return VerificationResult(
        case_id="CASE-SERVICE",
        status=status,
        observed_state={},
        expected_state=ExpectedFinancialState(),
        controls=controls,
        discrepancies=discrepancies,
    )


def make_investigation(
    *,
    status=InvestigationStatus.RESOLVED,
    explained=Decimal("500"),
    remaining=Decimal("0"),
    validated=True,
):
    return InvestigationResult(
        investigation_id="INV-SERVICE",
        case_id="CASE-SERVICE",
        discrepancy_id="DISC-SERVICE",
        status=status,
        explained_amount=explained,
        remaining_unexplained=remaining,
        supporting_evidence_ids=["EV-SERVICE"],
        conclusion="Evidence supports the investigation.",
        validated=validated,
    )


# ============================================================
# BASIC DECISION FLOW
# ============================================================


def test_verified_case_runs_through_complete_service():
    verification = make_verification(
        status=VerificationStatus.VERIFIED,
        discrepancy=False,
    )

    service = DecisionService()

    result = service.decide(
        verification
    )

    assert result.decision.decision == (
        DecisionOutcome.AUTO_RESOLVED
    )

    assert result.workflow.state == (
        CaseState.AUTO_RESOLVED
    )

    assert result.action.action_type == (
        "MARK_RESOLVED"
    )

    assert result.audit_entry_id


def test_pending_case_runs_through_service():
    verification = make_verification(
        status=VerificationStatus.PENDING,
        discrepancy=False,
    )

    service = DecisionService()

    result = service.decide(
        verification
    )

    assert result.decision.decision == (
        DecisionOutcome.PENDING
    )

    assert result.workflow.state == (
        CaseState.PENDING
    )

    assert result.action.action_type == (
        "MARK_PENDING"
    )


# ============================================================
# INVESTIGATION FLOW
# ============================================================


def test_resolved_investigation_can_auto_resolve():
    verification = make_verification()

    investigation = make_investigation()

    service = DecisionService()

    result = service.decide(
        verification,
        investigation,
    )

    assert result.decision.decision == (
        DecisionOutcome.AUTO_RESOLVED
    )

    assert result.workflow.state == (
        CaseState.AUTO_RESOLVED
    )

    assert result.decision.supporting_evidence_ids == [
        "EV-SERVICE"
    ]


def test_high_materiality_investigation_requires_review():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    result = service.decide(
        verification,
        investigation,
    )

    assert result.decision.decision == (
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )

    assert result.workflow.state == (
        CaseState.HUMAN_REVIEW
    )


def test_unresolved_blocking_case_becomes_blocked():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
        blocking=True,
    )

    investigation = make_investigation(
        status=InvestigationStatus.UNRESOLVED,
        explained=Decimal("0"),
        remaining=Decimal("5000"),
        validated=False,
    )

    service = DecisionService()

    result = service.decide(
        verification,
        investigation,
    )

    assert result.decision.decision == (
        DecisionOutcome.BLOCKED
    )

    assert result.workflow.state == (
        CaseState.BLOCKED
    )


# ============================================================
# HUMAN REVIEW
# ============================================================


def test_human_review_can_be_approved():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    result = service.decide(
        verification,
        investigation,
    )

    assert result.workflow.state == (
        CaseState.HUMAN_REVIEW
    )

    review = service.review(
        "CASE-SERVICE",
        ReviewAction.APPROVE,
        "Reviewed supporting evidence and approved.",
        reviewer_id="REVIEWER-001",
    )

    assert review.action == ReviewAction.APPROVE

    assert service.get_state(
        "CASE-SERVICE"
    ) == CaseState.APPROVED


def test_human_review_can_be_rejected():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    service.decide(
        verification,
        investigation,
    )

    service.review(
        "CASE-SERVICE",
        ReviewAction.REJECT,
        "Explanation requires further investigation.",
    )

    assert service.get_state(
        "CASE-SERVICE"
    ) == CaseState.REJECTED


def test_human_review_can_request_more_evidence():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    service.decide(
        verification,
        investigation,
    )

    service.review(
        "CASE-SERVICE",
        ReviewAction.REQUEST_MORE_EVIDENCE,
        "Need additional bank evidence.",
    )

    assert service.get_state(
        "CASE-SERVICE"
    ) == (
        CaseState.REQUEST_MORE_EVIDENCE
    )


# ============================================================
# REINVESTIGATION
# ============================================================


def test_rejected_case_can_enter_reinvestigation():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    service.decide(
        verification,
        investigation,
    )

    service.review(
        "CASE-SERVICE",
        ReviewAction.REJECT,
        "Need another investigation.",
    )

    state = service.request_reinvestigation(
        "CASE-SERVICE"
    )

    assert state == CaseState.REINVESTIGATION


def test_reinvestigation_can_return_to_investigation():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    service.decide(
        verification,
        investigation,
    )

    service.review(
        "CASE-SERVICE",
        ReviewAction.REJECT,
        "Need more evidence.",
    )

    service.request_reinvestigation(
        "CASE-SERVICE"
    )

    state = service.start_reinvestigation(
        "CASE-SERVICE"
    )

    assert state == CaseState.INVESTIGATION


# ============================================================
# REVIEW PACKAGE
# ============================================================


def test_review_package_can_be_created():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    service.decide(
        verification,
        investigation,
    )

    package = service.get_review_package(
        "CASE-SERVICE",
        discrepancy_id="DISC-SERVICE",
        control_id="SETTLEMENT_AMOUNT",
        investigation_status="RESOLVED",
        investigation_summary="Full explanation found.",
        investigation_conclusion="Settlement discrepancy explained.",
        evidence_ids=["EV-SERVICE"],
    )

    assert package.case_id == "CASE-SERVICE"
    assert package.discrepancy_id == (
        "DISC-SERVICE"
    )
    assert package.evidence_ids == [
        "EV-SERVICE"
    ]


# ============================================================
# AUDIT
# ============================================================


def test_decision_creates_audit_entry():
    verification = make_verification(
        status=VerificationStatus.VERIFIED,
        discrepancy=False,
    )

    service = DecisionService()

    service.decide(
        verification
    )

    history = service.get_audit_history(
        "CASE-SERVICE"
    )

    assert len(history) == 1

    assert history[0].decision == (
        DecisionOutcome.AUTO_RESOLVED
    )


def test_human_review_is_appended_to_audit_history():
    verification = make_verification(
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    service = DecisionService()

    service.decide(
        verification,
        investigation,
    )

    service.review(
        "CASE-SERVICE",
        ReviewAction.APPROVE,
        "Approved after review.",
    )

    history = service.get_audit_history(
        "CASE-SERVICE"
    )

    assert len(history) == 2

    assert history[0].decision == (
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )

    assert history[1].human_action == (
        ReviewAction.APPROVE
    )


# ============================================================
# SAFETY / IDENTITY
# ============================================================


def test_mismatched_investigation_is_rejected():
    verification = make_verification()

    investigation = make_investigation()

    investigation = investigation.model_copy(
        update={
            "case_id": "WRONG-CASE"
        }
    )

    service = DecisionService()

    with pytest.raises(ValueError):
        service.decide(
            verification,
            investigation,
        )


def test_review_without_decision_is_rejected():
    service = DecisionService()

    with pytest.raises(ValueError):
        service.review(
            "UNKNOWN-CASE",
            ReviewAction.APPROVE,
            "Approved.",
        )


def test_review_on_terminal_case_is_rejected():
    verification = make_verification(
        status=VerificationStatus.VERIFIED,
        discrepancy=False,
    )

    service = DecisionService()

    service.decide(
        verification
    )

    with pytest.raises(Exception):
        service.review(
            "CASE-SERVICE",
            ReviewAction.APPROVE,
            "This should not be allowed.",
        )