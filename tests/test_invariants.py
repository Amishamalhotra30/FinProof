from dataclasses import replace
from decimal import Decimal

from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.verification.invariants import (
    check_adjustment_amount,
    check_bank_credit_amount,
    check_fee_amount,
    check_refund_amount,
    check_settlement_amount,
    run_invariants,
)
from app.verification.models import (
    ControlStatus,
    ExpectedFinancialState,
    Severity,
)


def make_expected() -> ExpectedFinancialState:
    return ExpectedFinancialState(
        gross_captured=Decimal("50000.00"),
        total_refunded=Decimal("2000.00"),
        total_fees=Decimal("1000.00"),
        total_tax=Decimal("0.00"),
        total_adjustments=Decimal("500.00"),
        expected_settlement=Decimal("47500.00"),
        expected_bank_credit=Decimal("47500.00"),
    )


def make_observed() -> BatchReconstructionState:
    return BatchReconstructionState(
        chain_count=1,
        total_gross_amount=Decimal("50000.00"),
        total_refund_amount=Decimal("2000.00"),
        total_fee_amount=Decimal("1000.00"),
        total_adjustment_amount=Decimal("500.00"),
        total_settlement_amount=Decimal("47500.00"),
        total_bank_credit_amount=Decimal("47500.00"),
    )


def test_settlement_control_passes_when_values_match():
    result = check_settlement_amount(
        make_expected(),
        make_observed(),
    )

    assert result.status == ControlStatus.PASS
    assert result.difference == Decimal("0")
    assert result.blocking is False


def test_settlement_control_fails_when_values_differ():
    observed = make_observed()

    observed = BatchReconstructionState(
        **{
            **observed.__dict__,
            "total_settlement_amount": Decimal("47000.00"),
        }
    )

    result = check_settlement_amount(
        make_expected(),
        observed,
    )

    assert result.status == ControlStatus.FAIL
    assert result.difference == Decimal("-500.00")
    assert result.severity == Severity.HIGH
    assert result.blocking is True


def test_bank_control_passes_when_values_match():
    result = check_bank_credit_amount(
        make_expected(),
        make_observed(),
    )

    assert result.status == ControlStatus.PASS
    assert result.difference == Decimal("0")


def test_bank_control_fails_when_values_differ():
    observed = make_observed()

    observed = BatchReconstructionState(
        **{
            **observed.__dict__,
            "total_bank_credit_amount": Decimal("47000.00"),
        }
    )

    result = check_bank_credit_amount(
        make_expected(),
        observed,
    )

    assert result.status == ControlStatus.FAIL
    assert result.difference == Decimal("-500.00")


def test_bank_control_is_pending_without_expected_value():
    expected = ExpectedFinancialState(
        gross_captured=Decimal("50000.00"),
        total_refunded=Decimal("0.00"),
        total_fees=Decimal("1000.00"),
        total_adjustments=Decimal("0.00"),
        expected_settlement=Decimal("49000.00"),
        expected_bank_credit=None,
    )

    result = check_bank_credit_amount(
        expected,
        make_observed(),
    )

    assert result.status == ControlStatus.PENDING
    assert result.expected_value is None
    assert result.observed_value is None


def test_refund_control_passes():
    result = check_refund_amount(
        make_expected(),
        make_observed(),
    )

    assert result.status == ControlStatus.PASS


def test_fee_control_passes():
    result = check_fee_amount(
        make_expected(),
        make_observed(),
    )

    assert result.status == ControlStatus.PASS


def test_adjustment_control_passes():
    result = check_adjustment_amount(
        make_expected(),
        make_observed(),
    )

    assert result.status == ControlStatus.PASS


def test_run_invariants_returns_all_controls():
    results = run_invariants(
        make_expected(),
        make_observed(),
    )

    assert len(results) == 5

    assert {
        result.control_id
        for result in results
    } == {
        "SETTLEMENT_AMOUNT",
        "BANK_CREDIT_AMOUNT",
        "REFUND_AMOUNT",
        "FEE_AMOUNT",
        "ADJUSTMENT_AMOUNT",
    }


def test_invariants_do_not_modify_observed_state():
    observed = make_observed()

    before = replace(observed)

    run_invariants(
        make_expected(),
        observed,
    )

    assert observed == before


def test_invariants_do_not_modify_expected_state():
    expected = make_expected()

    before = expected.model_copy(deep=True)

    run_invariants(
        expected,
        make_observed(),
    )

    assert expected == before