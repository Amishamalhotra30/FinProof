from decimal import Decimal

from app.decisions.evaluator import DecisionEvaluator
from app.decisions.models import DecisionOutcome
from app.investigation.models import (
    InvestigationResult,
    InvestigationStatus,
)
from app.verification.models import (
    Discrepancy,
    ExpectedFinancialState,
    Materiality,
    VerificationResult,
    VerificationStatus,
)


CASE_ID = "P8-SAFETY-001"
DISC_ID = "P8-SAFETY-001-DISC"


def _passed_verification():
    return VerificationResult(
        case_id=CASE_ID,
        status=VerificationStatus.VERIFIED,
        expected_state=ExpectedFinancialState(),
        controls=[],
        discrepancies=[],
    )


def _failed_verification(
    amount=Decimal("500"),
    materiality=Materiality.LOW,
    blocking=False,
):
    discrepancy = Discrepancy(
        discrepancy_id=DISC_ID,
        control_id="SETTLEMENT_AMOUNT",
        expected_value=Decimal("1000"),
        observed_value=Decimal("500"),
        difference=amount,
        affected_event_ids=[],
        evidence_references=[],
        materiality=materiality,
        blocking=blocking,
    )

    return VerificationResult(
        case_id=CASE_ID,
        status=VerificationStatus.FAILED,
        expected_state=ExpectedFinancialState(),
        controls=[],
        discrepancies=[discrepancy],
    )


def _investigation(
    status=InvestigationStatus.RESOLVED,
    validated=True,
    explained=Decimal("500"),
    remaining=Decimal("0"),
    evidence=None,
):
    return InvestigationResult(
        investigation_id="P8-SAFETY-001-INV",
        case_id=CASE_ID,
        discrepancy_id=DISC_ID,
        status=status,
        hypotheses=[],
        explained_amount=explained,
        remaining_unexplained=remaining,
        supporting_evidence_ids=(
            evidence or []
        ),
        conclusion="Synthetic evaluation investigation.",
        validated=validated,
    )


def test_verified_case_can_auto_resolve():
    result = DecisionEvaluator().evaluate(
        _passed_verification()
    )

    assert (
        result.decision
        == DecisionOutcome.AUTO_RESOLVED
    )


def test_insufficient_evidence_requires_human_review():
    verification = _failed_verification()

    investigation = _investigation(
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        validated=True,
        explained=Decimal("0"),
        remaining=Decimal("500"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        == DecisionOutcome.HUMAN_REVIEW
    )


def test_contradiction_requires_human_review():
    verification = _failed_verification()

    investigation = _investigation(
        status=InvestigationStatus.CONTRADICTION,
        validated=True,
        explained=Decimal("0"),
        remaining=Decimal("500"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        == DecisionOutcome.HUMAN_REVIEW
    )


def test_unresolved_high_blocking_case_is_blocked():
    verification = _failed_verification(
        amount=Decimal("10000"),
        materiality=Materiality.HIGH,
        blocking=True,
    )

    investigation = _investigation(
        status=InvestigationStatus.UNRESOLVED,
        validated=True,
        explained=Decimal("5000"),
        remaining=Decimal("5000"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        == DecisionOutcome.BLOCKED
    )


def test_unresolved_high_nonblocking_requires_human_review():
    verification = _failed_verification(
        amount=Decimal("10000"),
        materiality=Materiality.HIGH,
        blocking=False,
    )

    investigation = _investigation(
        status=InvestigationStatus.UNRESOLVED,
        validated=True,
        explained=Decimal("5000"),
        remaining=Decimal("5000"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        == DecisionOutcome.HUMAN_REVIEW
    )


def test_resolved_but_not_validated_cannot_auto_resolve():
    verification = _failed_verification()

    investigation = _investigation(
        status=InvestigationStatus.RESOLVED,
        validated=False,
        explained=Decimal("500"),
        remaining=Decimal("0"),
        evidence=["EVENT-001"],
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        != DecisionOutcome.AUTO_RESOLVED
    )

    assert (
        result.decision
        == DecisionOutcome.HUMAN_REVIEW
    )


def test_resolved_with_remaining_amount_cannot_auto_resolve():
    verification = _failed_verification()

    investigation = _investigation(
        status=InvestigationStatus.RESOLVED,
        validated=True,
        explained=Decimal("400"),
        remaining=Decimal("100"),
        evidence=["EVENT-001"],
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        != DecisionOutcome.AUTO_RESOLVED
    )

    assert (
        result.decision
        == DecisionOutcome.HUMAN_REVIEW
    )


def test_high_materiality_resolved_case_requires_approval():
    verification = _failed_verification(
        amount=Decimal("5000"),
        materiality=Materiality.HIGH,
    )

    investigation = _investigation(
        status=InvestigationStatus.RESOLVED,
        validated=True,
        explained=Decimal("5000"),
        remaining=Decimal("0"),
        evidence=["EVENT-001"],
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        == DecisionOutcome.RESOLVED_WITH_APPROVAL
    )


def test_expected_pending_event_stays_pending():
    verification = VerificationResult(
        case_id=CASE_ID,
        status=VerificationStatus.PENDING,
        expected_state=ExpectedFinancialState(),
        controls=[],
        discrepancies=[],
    )

    result = DecisionEvaluator().evaluate(
        verification
    )

    assert (
        result.decision
        == DecisionOutcome.PENDING
    )


def test_decision_never_auto_resolves_contradiction():
    verification = _failed_verification()

    investigation = _investigation(
        status=InvestigationStatus.CONTRADICTION,
        validated=False,
        explained=Decimal("0"),
        remaining=Decimal("500"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        != DecisionOutcome.AUTO_RESOLVED
    )


def test_decision_never_auto_resolves_insufficient_evidence():
    verification = _failed_verification()

    investigation = _investigation(
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        validated=False,
        explained=Decimal("0"),
        remaining=Decimal("500"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert (
        result.decision
        != DecisionOutcome.AUTO_RESOLVED
    )