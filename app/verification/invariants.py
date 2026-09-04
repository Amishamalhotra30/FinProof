from decimal import Decimal

from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    ExpectedFinancialState,
    Severity,
)


def _difference(
    expected: Decimal,
    observed: Decimal,
) -> Decimal:
    return observed - expected


def check_settlement_amount(
    expected: ExpectedFinancialState,
    observed: BatchReconstructionState,
) -> ControlCheck:
    """
    Verify that observed settlement equals the independently
    calculated expected settlement.
    """

    expected_value = expected.expected_settlement
    observed_value = observed.total_settlement_amount

    difference = _difference(
        expected_value,
        observed_value,
    )

    passed = difference == Decimal("0")

    return ControlCheck(
        control_id="SETTLEMENT_AMOUNT",
        control_name="Settlement amount equals expected settlement",
        status=(
            ControlStatus.PASS
            if passed
            else ControlStatus.FAIL
        ),
        expected_value=expected_value,
        observed_value=observed_value,
        difference=difference,
        severity=(
            Severity.INFO
            if passed
            else Severity.HIGH
        ),
        blocking=not passed,
    )


def check_bank_credit_amount(
    expected: ExpectedFinancialState,
    observed: BatchReconstructionState,
) -> ControlCheck:
    """
    Verify observed bank credit against expected bank credit.

    If no independent expected bank amount is available,
    the control remains pending rather than comparing the
    observed value against itself.
    """

    if expected.expected_bank_credit is None:
        return ControlCheck(
            control_id="BANK_CREDIT_AMOUNT",
            control_name="Bank credit equals expected bank credit",
            status=ControlStatus.PENDING,
            severity=Severity.INFO,
            blocking=False,
        )

    expected_value = expected.expected_bank_credit
    observed_value = observed.total_bank_credit_amount

    difference = _difference(
        expected_value,
        observed_value,
    )

    passed = difference == Decimal("0")

    return ControlCheck(
        control_id="BANK_CREDIT_AMOUNT",
        control_name="Bank credit equals expected bank credit",
        status=(
            ControlStatus.PASS
            if passed
            else ControlStatus.FAIL
        ),
        expected_value=expected_value,
        observed_value=observed_value,
        difference=difference,
        severity=(
            Severity.INFO
            if passed
            else Severity.HIGH
        ),
        blocking=not passed,
    )


def check_refund_amount(
    expected: ExpectedFinancialState,
    observed: BatchReconstructionState,
) -> ControlCheck:
    """
    Verify that reconstructed refunds agree with the expected
    refund amount.
    """

    expected_value = expected.total_refunded
    observed_value = observed.total_refund_amount

    difference = _difference(
        expected_value,
        observed_value,
    )

    passed = difference == Decimal("0")

    return ControlCheck(
        control_id="REFUND_AMOUNT",
        control_name="Observed refunds equal expected refunds",
        status=(
            ControlStatus.PASS
            if passed
            else ControlStatus.FAIL
        ),
        expected_value=expected_value,
        observed_value=observed_value,
        difference=difference,
        severity=(
            Severity.INFO
            if passed
            else Severity.MEDIUM
        ),
        blocking=not passed,
    )


def check_fee_amount(
    expected: ExpectedFinancialState,
    observed: BatchReconstructionState,
) -> ControlCheck:
    """
    Verify that reconstructed fees agree with the expected
    fee amount.
    """

    expected_value = expected.total_fees
    observed_value = observed.total_fee_amount

    difference = _difference(
        expected_value,
        observed_value,
    )

    passed = difference == Decimal("0")

    return ControlCheck(
        control_id="FEE_AMOUNT",
        control_name="Observed fees equal expected fees",
        status=(
            ControlStatus.PASS
            if passed
            else ControlStatus.FAIL
        ),
        expected_value=expected_value,
        observed_value=observed_value,
        difference=difference,
        severity=(
            Severity.INFO
            if passed
            else Severity.MEDIUM
        ),
        blocking=not passed,
    )


def check_adjustment_amount(
    expected: ExpectedFinancialState,
    observed: BatchReconstructionState,
) -> ControlCheck:
    """
    Verify that reconstructed adjustments agree with the
    expected adjustment amount.
    """

    expected_value = expected.total_adjustments
    observed_value = observed.total_adjustment_amount

    difference = _difference(
        expected_value,
        observed_value,
    )

    passed = difference == Decimal("0")

    return ControlCheck(
        control_id="ADJUSTMENT_AMOUNT",
        control_name="Observed adjustments equal expected adjustments",
        status=(
            ControlStatus.PASS
            if passed
            else ControlStatus.FAIL
        ),
        expected_value=expected_value,
        observed_value=observed_value,
        difference=difference,
        severity=(
            Severity.INFO
            if passed
            else Severity.MEDIUM
        ),
        blocking=not passed,
    )


def run_invariants(
    expected: ExpectedFinancialState,
    observed: BatchReconstructionState,
) -> list[ControlCheck]:
    """
    Execute all currently defined deterministic financial
    invariants.

    The checks are independent and do not mutate either
    expected or observed state.
    """

    return [
        check_settlement_amount(
            expected,
            observed,
        ),
        check_bank_credit_amount(
            expected,
            observed,
        ),
        check_refund_amount(
            expected,
            observed,
        ),
        check_fee_amount(
            expected,
            observed,
        ),
        check_adjustment_amount(
            expected,
            observed,
        ),
    ]