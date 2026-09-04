from decimal import Decimal

from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.verification.models import (
    ExpectedFinancialState,
)


class ExpectedStateCalculator:
    """
    Calculates the financial state that should be expected
    from the reconstructed financial activity.

    This calculator intentionally does not use observed
    settlement or bank-credit amounts to determine the
    expected state.

    Phase 5 responsibility:
        What should the financial outcome be?

    It does not determine:
        - whether the observed outcome is correct
        - why a discrepancy exists
        - whether an event is missing
    """

    def calculate(
        self,
        state: BatchReconstructionState,
    ) -> ExpectedFinancialState:
        gross_captured = (
            state.total_gross_amount
        )

        total_refunded = (
            state.total_refund_amount
        )

        total_fees = (
            state.total_fee_amount
        )

        total_adjustments = (
            state.total_adjustment_amount
        )

        expected_settlement = (
            gross_captured
            - total_refunded
            - total_fees
            + total_adjustments
        )

        return ExpectedFinancialState(
            gross_captured=gross_captured,
            total_refunded=total_refunded,
            total_fees=total_fees,
            total_tax=Decimal("0"),
            total_adjustments=total_adjustments,
            expected_settlement=expected_settlement,
            expected_bank_credit=None,
        )


def calculate_expected_state(
    state: BatchReconstructionState,
) -> ExpectedFinancialState:
    """
    Convenience function for calculating expected state.
    """

    return ExpectedStateCalculator().calculate(
        state
    )