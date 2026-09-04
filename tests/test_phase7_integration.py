from decimal import Decimal

import pytest

from app.decisions.models import (
    CaseState,
    DecisionOutcome,
    DecisionPolicy,
    MaterialityLevel,
)
from app.decisions.service import DecisionService
from app.investigation.models import (
    InvestigationResult,
    InvestigationStatus,
)
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Discrepancy,
    Materiality,
    Severity,
    VerificationResult,
    VerificationStatus,
)


def _verification_passed(case_id: str) -> VerificationResult:
    return VerificationResult(
        case_id=case_id,
        status=VerificationStatus.VERIFIED,
        expected_state={},
        controls=[
            ControlCheck(
                control_id="TEST_CONTROL",
                control_name="Test control",
                status=ControlStatus.PASS,
                severity=Severity.INFO,
                blocking=False,
            )
        ],
        discrepancies=[],
    )


def _verification_pending(case_id: str) -> VerificationResult:
    return VerificationResult(
        case_id=case_id,
        status=VerificationStatus.PENDING,
        expected_state={},
        controls=[
            ControlCheck(
                control_id="TEST_CONTROL",
                control_name="Test control",
                status=ControlStatus.PENDING,
                severity=Severity.INFO,
                blocking=False,
            )
        ],
        discrepancies=[],
    )


def _verification_with_discrepancy(
    case_id: str,
    *,
    difference: Decimal = Decimal("500"),
    materiality: Materiality = Materiality.LOW,
) -> VerificationResult:
    discrepancy = Discrepancy(
        discrepancy_id=f"{case_id}-DISC",
        control_id="SETTLEMENT_AMOUNT",
        expected_value=Decimal("1000"),
        observed_value=Decimal("500"),
        difference=difference,
        affected_event_ids=["SETTLEMENT_001"],
        evidence_references=["SETTLEMENT_001"],
        materiality=materiality,
        blocking=False,
    )

    return VerificationResult(
        case_id=case_id,
        status=VerificationStatus.FAILED,
        expected_state={},
        controls=[
            ControlCheck(
                control_id="SETTLEMENT_AMOUNT",
                control_name="Settlement amount",
                status=ControlStatus.FAIL,
                expected_value=Decimal("1000"),
                observed_value=Decimal("500"),
                difference=difference,
                affected_event_ids=["SETTLEMENT_001"],
                supporting_evidence_ids=["SETTLEMENT_001"],
                severity=Severity.MEDIUM,
                blocking=False,
            )
        ],
        discrepancies=[discrepancy],
    )


def _resolved_investigation(
    case_id: str,
    discrepancy_id: str,
    *,
    amount: Decimal = Decimal("500"),
) -> InvestigationResult:
    return InvestigationResult(
        investigation_id=f"{case_id}-INV",
        case_id=case_id,
        discrepancy_id=discrepancy_id,
        status=InvestigationStatus.RESOLVED,
        hypotheses=[],
        explained_amount=amount,
        remaining_unexplained=Decimal("0"),
        supporting_evidence_ids=["SETTLEMENT_001"],
        conclusion="The discrepancy is fully explained by validated evidence.",
        validated=True,
    )


def _insufficient_investigation(
    case_id: str,
    discrepancy_id: str,
) -> InvestigationResult:
    return InvestigationResult(
        investigation_id=f"{case_id}-INV",
        case_id=case_id,
        discrepancy_id=discrepancy_id,
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        hypotheses=[],
        explained_amount=Decimal("0"),
        remaining_unexplained=Decimal("500"),
        supporting_evidence_ids=[],
        conclusion="Required evidence is unavailable.",
        validated=True,
    )


def test_phase7_end_to_end_all_controls_pass():
    service = DecisionService()

    verification = _verification_passed("P7-E2E-PASS")

    result = service.decide(verification)

    assert result.decision.decision == DecisionOutcome.AUTO_RESOLVED
    assert result.workflow.state == CaseState.AUTO_RESOLVED
    assert result.action.action_type == "MARK_RESOLVED"

    audit_history = service.get_audit_history("P7-E2E-PASS")

    assert len(audit_history) == 1
    assert audit_history[0].decision == DecisionOutcome.AUTO_RESOLVED
    assert audit_history[0].case_id == "P7-E2E-PASS"


def test_phase7_end_to_end_pending_verification():
    service = DecisionService()

    verification = _verification_pending("P7-E2E-PENDING")

    result = service.decide(verification)

    assert result.decision.decision == DecisionOutcome.PENDING
    assert result.workflow.state == CaseState.PENDING
    assert result.action.action_type == "MARK_PENDING"

    audit_history = service.get_audit_history("P7-E2E-PENDING")

    assert len(audit_history) == 1
    assert audit_history[0].decision == DecisionOutcome.PENDING


def test_phase7_end_to_end_investigation_to_auto_resolution():
    service = DecisionService(
        policy=DecisionPolicy(
            auto_resolution_threshold=Decimal("1000")
        )
    )

    verification = _verification_with_discrepancy(
        "P7-E2E-INVESTIGATED"
    )

    investigation = _resolved_investigation(
        "P7-E2E-INVESTIGATED",
        "P7-E2E-INVESTIGATED-DISC",
    )

    result = service.decide(
        verification,
        investigation,
    )

    assert result.decision.decision == DecisionOutcome.AUTO_RESOLVED
    assert result.workflow.state == CaseState.AUTO_RESOLVED
    assert result.action.action_type == "MARK_RESOLVED"

    assert (
        result.decision.supporting_evidence_ids
        == ["SETTLEMENT_001"]
    )

    audit_history = service.get_audit_history(
        "P7-E2E-INVESTIGATED"
    )

    assert len(audit_history) == 1
    assert audit_history[0].evidence_ids == [
        "SETTLEMENT_001"
    ]


def test_phase7_end_to_end_material_explanation_requires_approval():
    service = DecisionService()

    verification = _verification_with_discrepancy(
        "P7-E2E-MATERIAL",
        difference=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = _resolved_investigation(
        "P7-E2E-MATERIAL",
        "P7-E2E-MATERIAL-DISC",
        amount=Decimal("5000"),
    )

    result = service.decide(
        verification,
        investigation,
    )

    assert (
        result.decision.decision
        == DecisionOutcome.RESOLVED_WITH_APPROVAL
    )

    assert result.workflow.state == CaseState.HUMAN_REVIEW
    assert result.action.action_type == "CREATE_HUMAN_REVIEW"

    assert result.decision.supporting_evidence_ids == [
        "SETTLEMENT_001"
    ]


def test_phase7_end_to_end_insufficient_evidence_requires_human_review():
    service = DecisionService()

    verification = _verification_with_discrepancy(
        "P7-E2E-INSUFFICIENT"
    )

    investigation = _insufficient_investigation(
        "P7-E2E-INSUFFICIENT",
        "P7-E2E-INSUFFICIENT-DISC",
    )

    result = service.decide(
        verification,
        investigation,
    )

    assert result.decision.decision == DecisionOutcome.HUMAN_REVIEW
    assert result.workflow.state == CaseState.HUMAN_REVIEW
    assert result.action.action_type == "CREATE_HUMAN_REVIEW"

    assert (
        result.decision.supporting_evidence_ids == []
    )

    audit_history = service.get_audit_history(
        "P7-E2E-INSUFFICIENT"
    )

    assert len(audit_history) == 1
    assert (
        audit_history[0].decision
        == DecisionOutcome.HUMAN_REVIEW
    )