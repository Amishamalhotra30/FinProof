from decimal import Decimal

from app.investigation.case_builder import (
    InvestigationCaseBuilder,
    build_investigation_case,
    build_investigation_cases,
)
from app.verification.models import (
    Discrepancy,
    ExpectedFinancialState,
    VerificationResult,
    VerificationStatus,
    ControlCheck,
    ControlStatus,
    Severity,
)


def make_verification(
    *,
    discrepancies=None,
):
    return VerificationResult(
        case_id="CASE_0001",
        status=VerificationStatus.FAILED,
        observed_state={
            "gross_captured": Decimal("50000.00"),
            "total_refunded": Decimal("0.00"),
            "total_fees": Decimal("1000.00"),
            "total_adjustments": Decimal("0.00"),
            "total_settled": Decimal("49000.00"),
            "total_bank_credited": Decimal("45000.00"),
        },
        expected_state=ExpectedFinancialState(
            gross_captured=Decimal("50000.00"),
            total_refunded=Decimal("0.00"),
            total_fees=Decimal("1000.00"),
            total_tax=Decimal("0.00"),
            total_adjustments=Decimal("0.00"),
            expected_settlement=Decimal("49000.00"),
            expected_bank_credit=None,
        ),
        controls=[],
        discrepancies=discrepancies or [],
        processing_time_ms=Decimal("1.00"),
    )


def make_discrepancy(
    discrepancy_id="DISC_BANK_CREDIT_AMOUNT",
):
    return Discrepancy(
        discrepancy_id=discrepancy_id,
        control_id="BANK_CREDIT_AMOUNT",
        expected_value=Decimal("49000.00"),
        observed_value=Decimal("45000.00"),
        difference=Decimal("-4000.00"),
        relative_difference=Decimal(
            "0.08163265306122448979591836735"
        ),
        affected_event_ids=[
            "PAYMENT_0001",
            "SETTLEMENT_0001",
            "BANK_0001",
        ],
        evidence_references=[],
        materiality="HIGH",
        blocking=True,
    )


def test_builder_preserves_phase5_case_identity():
    verification = make_verification()
    discrepancy = make_discrepancy()

    case = InvestigationCaseBuilder().build(
        verification,
        discrepancy,
    )

    assert case.case_id == "CASE_0001"
    assert (
        case.discrepancy_id
        == "DISC_BANK_CREDIT_AMOUNT"
    )


def test_builder_preserves_discrepancy_values():
    verification = make_verification()
    discrepancy = make_discrepancy()

    case = InvestigationCaseBuilder().build(
        verification,
        discrepancy,
    )

    assert (
        case.expected_value
        == Decimal("49000.00")
    )

    assert (
        case.observed_value
        == Decimal("45000.00")
    )

    assert (
        case.difference
        == Decimal("-4000.00")
    )


def test_builder_preserves_affected_events():
    verification = make_verification()
    discrepancy = make_discrepancy()

    case = InvestigationCaseBuilder().build(
        verification,
        discrepancy,
    )

    assert case.affected_event_ids == [
        "PAYMENT_0001",
        "SETTLEMENT_0001",
        "BANK_0001",
    ]


def test_builder_preserves_financial_state():
    verification = make_verification()
    discrepancy = make_discrepancy()

    case = InvestigationCaseBuilder().build(
        verification,
        discrepancy,
    )

    assert (
        case.observed_state["total_bank_credited"]
        == Decimal("45000.00")
    )

    assert (
        case.expected_state["expected_settlement"]
        == Decimal("49000.00")
    )


def test_builder_does_not_mutate_event_ids():
    verification = make_verification()
    discrepancy = make_discrepancy()

    original = list(
        discrepancy.affected_event_ids
    )

    case = InvestigationCaseBuilder().build(
        verification,
        discrepancy,
    )

    case.affected_event_ids.append(
        "NEW_EVENT"
    )

    assert (
        discrepancy.affected_event_ids
        == original
    )


def test_convenience_builder_matches_class_builder():
    verification = make_verification()
    discrepancy = make_discrepancy()

    expected = InvestigationCaseBuilder().build(
        verification,
        discrepancy,
    )

    actual = build_investigation_case(
        verification,
        discrepancy,
    )

    assert actual == expected


def test_build_all_discrepancies():
    first = make_discrepancy(
        "DISC_BANK_CREDIT_AMOUNT"
    )

    second = make_discrepancy(
        "DISC_SETTLEMENT_AMOUNT"
    )

    verification = make_verification(
        discrepancies=[
            first,
            second,
        ]
    )

    cases = build_investigation_cases(
        verification
    )

    assert len(cases) == 2

    assert cases[0].discrepancy_id == (
        "DISC_BANK_CREDIT_AMOUNT"
    )

    assert cases[1].discrepancy_id == (
        "DISC_SETTLEMENT_AMOUNT"
    )


def test_no_discrepancies_produces_empty_investigation_list():
    verification = make_verification(
        discrepancies=[]
    )

    cases = build_investigation_cases(
        verification
    )

    assert cases == []