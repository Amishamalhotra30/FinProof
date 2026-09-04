from dataclasses import dataclass
from decimal import Decimal

from app.reconstruction.event_chain import EventChain
from app.reconstruction.state_reconstructor import (
    ObservedFinancialState,
    StateReconstructor,
)


@dataclass(frozen=True)
class BatchReconstructionState:
    """
    Aggregate observed financial state across all reconstructed
    event chains in a batch.

    This is descriptive aggregation only. It does not determine
    financial correctness or investigate discrepancies.
    """

    chain_count: int

    total_gross_amount: Decimal = Decimal("0")
    total_refund_amount: Decimal = Decimal("0")
    total_fee_amount: Decimal = Decimal("0")
    total_adjustment_amount: Decimal = Decimal("0")
    total_settlement_amount: Decimal = Decimal("0")
    total_bank_credit_amount: Decimal = Decimal("0")

    payment_event_count: int = 0
    refund_event_count: int = 0
    fee_event_count: int = 0
    adjustment_event_count: int = 0
    settlement_event_count: int = 0
    bank_event_count: int = 0

    @property
    def total_observed_net_amount(self) -> Decimal:
        return (
            self.total_gross_amount
            - self.total_refund_amount
            - self.total_fee_amount
            + self.total_adjustment_amount
        )


class BatchStateReconstructor:
    """
    Aggregates ObservedFinancialState objects for an entire batch.

    It does not create events, infer missing events, or determine
    whether the resulting financial state is correct.
    """

    def __init__(
        self,
        state_reconstructor: StateReconstructor | None = None,
    ):
        self.state_reconstructor = (
            state_reconstructor
            or StateReconstructor()
        )

    def reconstruct(
        self,
        chains: list[EventChain],
        events,
    ) -> BatchReconstructionState:
        """
        Reconstruct and aggregate every supplied chain.
        """

        states: list[ObservedFinancialState] = []

        for chain in chains:
            states.append(
                self.state_reconstructor.reconstruct(
                    chain,
                    events,
                )
            )

        return self.aggregate(states)

    @staticmethod
    def aggregate(
        states: list[ObservedFinancialState],
    ) -> BatchReconstructionState:
        """
        Aggregate already reconstructed chain states.

        The input states are not modified.
        """

        total_gross = Decimal("0")
        total_refunds = Decimal("0")
        total_fees = Decimal("0")
        total_adjustments = Decimal("0")
        total_settlements = Decimal("0")
        total_bank_credit = Decimal("0")

        payment_count = 0
        refund_count = 0
        fee_count = 0
        adjustment_count = 0
        settlement_count = 0
        bank_count = 0

        for state in states:

            total_gross += state.gross_amount
            total_refunds += state.refund_amount
            total_fees += state.fee_amount
            total_adjustments += state.adjustment_amount
            total_settlements += state.settlement_amount
            total_bank_credit += state.bank_credit_amount

            payment_count += len(
                state.payment_event_ids
            )

            refund_count += len(
                state.refund_event_ids
            )

            fee_count += len(
                state.fee_event_ids
            )

            adjustment_count += len(
                state.adjustment_event_ids
            )

            settlement_count += len(
                state.settlement_event_ids
            )

            bank_count += len(
                state.bank_event_ids
            )

        return BatchReconstructionState(
            chain_count=len(states),
            total_gross_amount=total_gross,
            total_refund_amount=total_refunds,
            total_fee_amount=total_fees,
            total_adjustment_amount=total_adjustments,
            total_settlement_amount=total_settlements,
            total_bank_credit_amount=total_bank_credit,
            payment_event_count=payment_count,
            refund_event_count=refund_count,
            fee_event_count=fee_count,
            adjustment_event_count=adjustment_count,
            settlement_event_count=settlement_count,
            bank_event_count=bank_count,
        )