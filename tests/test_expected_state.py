from decimal import Decimal

from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.verification.expected_state import (
    ExpectedStateCalculator,
)


def make_state() -> BatchReconstructionState:
    return BatchReconstructionState(
        chain_count=1,
        total_gross_amount=Decimal("50000.00"),
        total_refund_amount=Decimal("2000.00"),
        total_fee_amount=Decimal("1000.00"),
        total_adjustment_amount=Decimal("500.00"),
        total_settlement_amount=Decimal("47500.00"),
        total_bank_credit_amount=Decimal("47500.00"),
    )


def test_expected_settlement_is_calculated_independently():
    state = make_state()

    expected = ExpectedStateCalculator().calculate(
        state
    )

    assert (
        expected.expected_settlement
        == Decimal("47500.00")
    )


def test_expected_state_does_not_copy_observed_settlement():
    state = BatchReconstructionState(
        chain_count=1,
        total_gross_amount=Decimal("50000.00"),
        total_refund_amount=Decimal("2000.00"),
        total_fee_amount=Decimal("1000.00"),
        total_adjustment_amount=Decimal("0.00"),
        total_settlement_amount=Decimal("999.00"),
        total_bank_credit_amount=Decimal("999.00"),
    )

    expected = ExpectedStateCalculator().calculate(
        state
    )

    assert (
        expected.expected_settlement
        == Decimal("47000.00")
    )


def test_expected_bank_credit_is_not_copied_from_observed():
    state = make_state()

    expected = ExpectedStateCalculator().calculate(
        state
    )

    assert expected.expected_bank_credit is None


def test_expected_state_preserves_observed_components():
    state = make_state()

    expected = ExpectedStateCalculator().calculate(
        state
    )

    assert expected.gross_captured == Decimal(
        "50000.00"
    )

    assert expected.total_refunded == Decimal(
        "2000.00"
    )

    assert expected.total_fees == Decimal(
        "1000.00"
    )

    assert expected.total_adjustments == Decimal(
        "500.00"
    )