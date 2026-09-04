from decimal import Decimal

from app.investigation.hypotheses import (
    HypothesisGenerator,
    generate_hypotheses,
)
from app.investigation.models import (
    HypothesisStatus,
    HypothesisType,
    InvestigationCase,
)


def make_case(
    control_failure: str,
) -> InvestigationCase:
    return InvestigationCase(
        case_id="CASE_0001",
        discrepancy_id="DISC_TEST",
        control_failure=control_failure,
        affected_event_ids=[
            "PAYMENT_1",
            "SETTLEMENT_1",
        ],
        expected_value=Decimal("50000.00"),
        observed_value=Decimal("47000.00"),
        difference=Decimal("-3000.00"),
        expected_state={
            "gross_captured": Decimal("50000.00"),
            "expected_settlement": Decimal("50000.00"),
        },
        observed_state={
            "gross_captured": Decimal("50000.00"),
            "total_settled": Decimal("47000.00"),
        },
    )


def test_settlement_amount_generates_bounded_hypotheses():
    case = make_case("SETTLEMENT_AMOUNT")

    hypotheses = HypothesisGenerator().generate(case)

    assert [
        hypothesis.hypothesis_type
        for hypothesis in hypotheses
    ] == [
        HypothesisType.PARTIAL_SETTLEMENT,
        HypothesisType.BUNDLED_SETTLEMENT,
        HypothesisType.REFUND,
        HypothesisType.FEE,
        HypothesisType.TAX,
        HypothesisType.ADJUSTMENT,
        HypothesisType.SOURCE_DATA_ERROR,
    ]


def test_bank_credit_amount_generates_relevant_hypotheses():
    case = make_case("BANK_CREDIT_AMOUNT")

    hypotheses = generate_hypotheses(case)

    assert {
        hypothesis.hypothesis_type
        for hypothesis in hypotheses
    } == {
        HypothesisType.PARTIAL_SETTLEMENT,
        HypothesisType.BUNDLED_SETTLEMENT,
        HypothesisType.MISSING_EVENT,
        HypothesisType.SOURCE_DATA_ERROR,
    }


def test_duplicate_control_generates_duplicate_hypothesis():
    case = make_case("DUPLICATE_EVENT")

    hypotheses = generate_hypotheses(case)

    assert [
        hypothesis.hypothesis_type
        for hypothesis in hypotheses
    ] == [
        HypothesisType.DUPLICATE_EVENT,
        HypothesisType.SOURCE_DATA_ERROR,
    ]


def test_temporal_control_generates_timing_hypothesis():
    case = make_case("EVENT_ORDERING")

    hypotheses = generate_hypotheses(case)

    assert [
        hypothesis.hypothesis_type
        for hypothesis in hypotheses
    ] == [
        HypothesisType.TIMING_DIFFERENCE,
        HypothesisType.SOURCE_DATA_ERROR,
    ]


def test_unknown_control_has_safe_fallback():
    case = make_case("UNKNOWN_CONTROL")

    hypotheses = generate_hypotheses(case)

    assert [
        hypothesis.hypothesis_type
        for hypothesis in hypotheses
    ] == [
        HypothesisType.SOURCE_DATA_ERROR,
        HypothesisType.UNDETERMINED,
    ]


def test_hypotheses_start_undetermined():
    case = make_case("SETTLEMENT_BANK_COMPLETENESS")

    hypotheses = generate_hypotheses(case)

    assert hypotheses

    assert all(
        hypothesis.status
        == HypothesisStatus.UNDETERMINED
        for hypothesis in hypotheses
    )


def test_hypothesis_ids_are_stable():
    case = make_case("DUPLICATE_EVENT")

    first = generate_hypotheses(case)
    second = generate_hypotheses(case)

    assert [
        hypothesis.hypothesis_id
        for hypothesis in first
    ] == [
        hypothesis.hypothesis_id
        for hypothesis in second
    ]


def test_hypothesis_ids_are_unique():
    case = make_case("SETTLEMENT_AMOUNT")

    hypotheses = generate_hypotheses(case)

    ids = [
        hypothesis.hypothesis_id
        for hypothesis in hypotheses
    ]

    assert len(ids) == len(set(ids))


def test_generation_does_not_modify_case():
    case = make_case("FEE_AMOUNT")

    original = case.model_dump()

    generate_hypotheses(case)

    assert case.model_dump() == original