from decimal import Decimal

import pytest

from app.decisions.evaluator import (
    DecisionEvaluator,
)
from app.decisions.models import (
    DecisionOutcome,
    MaterialityLevel,
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
    discrepancies=None,
    controls=None,
):
    return VerificationResult(
        case_id="CASE-EVAL",
        status=status,
        observed_state={},
        expected_state=ExpectedFinancialState(),
        controls=controls or [],
        discrepancies=discrepancies or [],
    )


def make_discrepancy(
    *,
    discrepancy_id="DISC-001",
    difference=Decimal("500"),
    materiality=Materiality.LOW,
    blocking=False,
):
    return Discrepancy(
        discrepancy_id=discrepancy_id,
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


def make_investigation(
    *,
    status=InvestigationStatus.RESOLVED,
    explained=Decimal("500"),
    remaining=Decimal("0"),
    validated=True,
    discrepancy_id="DISC-001",
    evidence=None,
):
    return InvestigationResult(
        investigation_id="INV-001",
        case_id="CASE-EVAL",
        discrepancy_id=discrepancy_id,
        status=status,
        explained_amount=explained,
        remaining_unexplained=remaining,
        supporting_evidence_ids=(
            ["EV-001"]
            if evidence is None
            else evidence
        ),
        conclusion="Evidence supports the explanation.",
        validated=validated,
    )


# ============================================================
# VERIFIED
# ============================================================


def test_verified_case_becomes_auto_resolved():
    verification = make_verification(
        status=VerificationStatus.VERIFIED,
        controls=[
            ControlCheck(
                control_id="SETTLEMENT_AMOUNT",
                control_name="Settlement amount",
                status=ControlStatus.PASS,
            )
        ],
    )

    result = DecisionEvaluator().evaluate(
        verification
    )

    assert result.decision == (
        DecisionOutcome.AUTO_RESOLVED
    )

    assert result.financial_impact == Decimal("0")


# ============================================================
# PENDING
# ============================================================


def test_pending_verification_becomes_pending():
    verification = make_verification(
        status=VerificationStatus.PENDING
    )

    result = DecisionEvaluator().evaluate(
        verification
    )

    assert result.decision == (
        DecisionOutcome.PENDING
    )


# ============================================================
# RESOLVED INVESTIGATION
# ============================================================


def test_validated_resolved_low_value_auto_resolves():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                difference=Decimal("500"),
                materiality=Materiality.LOW,
            )
        ]
    )

    investigation = make_investigation(
        explained=Decimal("500"),
        remaining=Decimal("0"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert result.decision == (
        DecisionOutcome.AUTO_RESOLVED
    )

    assert result.financial_impact == Decimal(
        "500"
    )

    assert result.materiality == (
        MaterialityLevel.LOW
    )

    assert result.supporting_evidence_ids == [
        "EV-001"
    ]


def test_high_materiality_resolved_case_requires_approval():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                difference=Decimal("5000"),
                materiality=Materiality.HIGH,
            )
        ]
    )

    investigation = make_investigation(
        explained=Decimal("5000"),
        remaining=Decimal("0"),
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert result.decision == (
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )

    assert result.materiality == (
        MaterialityLevel.HIGH
    )


# ============================================================
# INVESTIGATION STATUS
# ============================================================


def test_insufficient_evidence_requires_human_review():
    verification = make_verification(
        discrepancies=[
            make_discrepancy()
        ]
    )

    investigation = make_investigation(
        status=(
            InvestigationStatus.INSUFFICIENT_EVIDENCE
        ),
        explained=Decimal("0"),
        remaining=Decimal("500"),
        validated=False,
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )


def test_contradiction_requires_human_review():
    verification = make_verification(
        discrepancies=[
            make_discrepancy()
        ]
    )

    investigation = make_investigation(
        status=InvestigationStatus.CONTRADICTION,
        explained=Decimal("0"),
        remaining=Decimal("500"),
        validated=False,
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )


def test_unresolved_blocking_case_is_blocked():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                difference=Decimal("5000"),
                materiality=Materiality.HIGH,
                blocking=True,
            )
        ]
    )

    investigation = make_investigation(
        status=InvestigationStatus.UNRESOLVED,
        explained=Decimal("0"),
        remaining=Decimal("5000"),
        validated=False,
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert result.decision == (
        DecisionOutcome.BLOCKED
    )


# ============================================================
# FACT CONSTRUCTION
# ============================================================


def test_materiality_is_mapped_from_phase5():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                materiality=Materiality.MEDIUM
            )
        ]
    )

    facts = DecisionEvaluator().build_facts(
        verification
    )

    assert facts.materiality == (
        MaterialityLevel.MEDIUM
    )


def test_financial_impact_comes_from_phase5():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                difference=Decimal("-750")
            )
        ]
    )

    facts = DecisionEvaluator().build_facts(
        verification
    )

    assert facts.financial_impact == Decimal(
        "750"
    )


def test_multiple_discrepancies_sum_financial_impact():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                discrepancy_id="DISC-001",
                difference=Decimal("300"),
            ),
            make_discrepancy(
                discrepancy_id="DISC-002",
                difference=Decimal("-200"),
            ),
        ]
    )

    facts = DecisionEvaluator().build_facts(
        verification
    )

    assert facts.financial_impact == Decimal(
        "500"
    )


def test_investigation_validation_is_preserved():
    verification = make_verification(
        discrepancies=[
            make_discrepancy()
        ]
    )

    investigation = make_investigation(
        validated=True
    )

    facts = DecisionEvaluator().build_facts(
        verification,
        investigation,
    )

    assert facts.investigation_validated is True


def test_unvalidated_investigation_cannot_be_evidence_sufficient():
    verification = make_verification(
        discrepancies=[
            make_discrepancy()
        ]
    )

    investigation = make_investigation(
        validated=False
    )

    facts = DecisionEvaluator().build_facts(
        verification,
        investigation,
    )

    assert facts.evidence_sufficient is False


# ============================================================
# IDENTITY SAFETY
# ============================================================


def test_mismatched_case_ids_are_rejected():
    verification = make_verification(
        discrepancies=[
            make_discrepancy()
        ]
    )

    investigation = make_investigation()

    investigation = investigation.model_copy(
        update={
            "case_id": "DIFFERENT-CASE"
        }
    )

    with pytest.raises(ValueError):
        DecisionEvaluator().build_facts(
            verification,
            investigation,
        )


def test_mismatched_discrepancy_id_is_rejected():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                discrepancy_id="DISC-001"
            )
        ]
    )

    investigation = make_investigation(
        discrepancy_id="DISC-999"
    )

    with pytest.raises(ValueError):
        DecisionEvaluator().build_facts(
            verification,
            investigation,
        )


# ============================================================
# SAFETY
# ============================================================


def test_investigation_does_not_override_financial_impact():
    verification = make_verification(
        discrepancies=[
            make_discrepancy(
                difference=Decimal("1000")
            )
        ]
    )

    investigation = make_investigation(
        explained=Decimal("1000"),
        remaining=Decimal("0"),
    )

    facts = DecisionEvaluator().build_facts(
        verification,
        investigation,
    )

    assert facts.financial_impact == Decimal(
        "1000"
    )


def test_no_discrepancy_has_zero_financial_impact():
    verification = make_verification(
        status=VerificationStatus.VERIFIED
    )

    facts = DecisionEvaluator().build_facts(
        verification
    )

    assert facts.financial_impact == Decimal(
        "0"
    )


def test_investigation_evidence_is_not_invented():
    verification = make_verification(
        discrepancies=[
            make_discrepancy()
        ]
    )

    investigation = make_investigation(
        evidence=[]
    )

    result = DecisionEvaluator().evaluate(
        verification,
        investigation,
    )

    assert result.supporting_evidence_ids == []