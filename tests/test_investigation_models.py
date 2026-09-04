from decimal import Decimal

from app.investigation.models import (
    EvidenceRelation,
    HypothesisFinding,
    HypothesisStatus,
    HypothesisType,
    InvestigationCase,
    InvestigationEvidence,
    InvestigationHypothesis,
    InvestigationResult,
    InvestigationStatus,
)


def test_investigation_case_creation():
    case = InvestigationCase(
        case_id="CASE_0001",
        discrepancy_id="DISC_BANK_CREDIT_AMOUNT",
        control_failure="BANK_CREDIT_AMOUNT",
        affected_event_ids=[
            "PAYMENT_0001",
            "SETTLEMENT_0001",
            "BANK_0001",
        ],
        expected_value=Decimal("44000.00"),
        observed_value=Decimal("49000.00"),
        difference=Decimal("5000.00"),
        expected_state={
            "expected_settlement": Decimal(
                "44000.00"
            )
        },
        observed_state={
            "bank_credit": Decimal(
                "49000.00"
            )
        },
    )

    assert case.case_id == "CASE_0001"
    assert (
        case.discrepancy_id
        == "DISC_BANK_CREDIT_AMOUNT"
    )
    assert case.difference == Decimal("5000.00")
    assert len(case.affected_event_ids) == 3


def test_hypothesis_type_is_bounded():
    assert HypothesisType.REFUND.value == "REFUND"
    assert (
        HypothesisType.ADJUSTMENT.value
        == "ADJUSTMENT"
    )
    assert (
        HypothesisType.DUPLICATE_EVENT.value
        == "DUPLICATE_EVENT"
    )


def test_hypothesis_statuses():
    assert (
        HypothesisStatus.SUPPORTED.value
        == "SUPPORTED"
    )

    assert (
        HypothesisStatus.CONTRADICTED.value
        == "CONTRADICTED"
    )

    assert (
        HypothesisStatus.UNDETERMINED.value
        == "UNDETERMINED"
    )


def test_evidence_creation():
    evidence = InvestigationEvidence(
        evidence_id="EV_001",
        source="refunds",
        record_id="REFUND_001",
        amount=Decimal("5000.00"),
        timestamp="2026-08-30T10:00:00",
        relationship=EvidenceRelation.SUPPORTS,
        description="Refund linked to payment",
    )

    assert evidence.evidence_id == "EV_001"
    assert evidence.record_id == "REFUND_001"
    assert evidence.amount == Decimal("5000.00")
    assert (
        evidence.relationship
        == EvidenceRelation.SUPPORTS
    )


def test_hypothesis_creation():
    hypothesis = InvestigationHypothesis(
        hypothesis_id="H1",
        hypothesis_type=HypothesisType.REFUND,
        status=HypothesisStatus.SUPPORTED,
        description="Refund explains the discrepancy",
        evidence_ids=[
            "EV_001",
            "EV_002",
        ],
        explained_amount=Decimal("5000.00"),
    )

    assert hypothesis.hypothesis_id == "H1"
    assert (
        hypothesis.hypothesis_type
        == HypothesisType.REFUND
    )
    assert (
        hypothesis.status
        == HypothesisStatus.SUPPORTED
    )
    assert hypothesis.explained_amount == Decimal(
        "5000.00"
    )
    assert len(hypothesis.evidence_ids) == 2


def test_hypothesis_finding_creation():
    finding = HypothesisFinding(
        hypothesis_type=HypothesisType.REFUND,
        status=HypothesisStatus.SUPPORTED,
        explained_amount=Decimal("5000.00"),
        evidence_ids=["EV_001"],
        reasoning="Matching refund found.",
    )

    assert (
        finding.hypothesis_type
        == HypothesisType.REFUND
    )

    assert (
        finding.status
        == HypothesisStatus.SUPPORTED
    )

    assert finding.explained_amount == Decimal(
        "5000.00"
    )


def test_resolved_investigation_result():
    result = InvestigationResult(
        investigation_id="INV_0001",
        case_id="CASE_0001",
        discrepancy_id="DISC_0001",
        status=InvestigationStatus.RESOLVED,
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=HypothesisType.REFUND,
                status=HypothesisStatus.SUPPORTED,
                explained_amount=Decimal(
                    "5000.00"
                ),
                evidence_ids=["EV_001"],
            )
        ],
        explained_amount=Decimal("5000.00"),
        remaining_unexplained=Decimal("0.00"),
        supporting_evidence_ids=["EV_001"],
        conclusion="Refund explains discrepancy.",
        validated=True,
    )

    assert (
        result.status
        == InvestigationStatus.RESOLVED
    )

    assert result.explained_amount == Decimal(
        "5000.00"
    )

    assert result.remaining_unexplained == Decimal(
        "0.00"
    )

    assert result.validated is True


def test_unresolved_investigation_result():
    result = InvestigationResult(
        investigation_id="INV_0002",
        case_id="CASE_0002",
        discrepancy_id="DISC_0002",
        status=InvestigationStatus.UNRESOLVED,
        explained_amount=Decimal("0.00"),
        remaining_unexplained=Decimal("17500.00"),
        conclusion=(
            "No available evidence explains "
            "the discrepancy."
        ),
    )

    assert (
        result.status
        == InvestigationStatus.UNRESOLVED
    )

    assert result.explained_amount == Decimal(
        "0.00"
    )

    assert result.remaining_unexplained == Decimal(
        "17500.00"
    )

    assert result.validated is False