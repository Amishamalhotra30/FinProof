from dataclasses import dataclass
from decimal import Decimal

from app.domain.events import FinancialEvent
from app.domain.enums import EventType
from app.reconstruction.event_chain import EventChain


@dataclass(frozen=True)
class ObservedFinancialState:
    """
    Financial state reconstructed only from observed events.

    Values are derived from records that actually exist in the
    reconstructed event chain. No missing financial events are
    created or inferred.
    """

    chain_id: str

    gross_amount: Decimal = Decimal("0")
    refund_amount: Decimal = Decimal("0")
    fee_amount: Decimal = Decimal("0")
    adjustment_amount: Decimal = Decimal("0")
    settlement_amount: Decimal = Decimal("0")
    bank_credit_amount: Decimal = Decimal("0")

    payment_event_ids: tuple[str, ...] = ()
    refund_event_ids: tuple[str, ...] = ()
    fee_event_ids: tuple[str, ...] = ()
    adjustment_event_ids: tuple[str, ...] = ()
    settlement_event_ids: tuple[str, ...] = ()
    bank_event_ids: tuple[str, ...] = ()

    @property
    def observed_net_amount(self) -> Decimal:
        """
        Net amount implied by observed payment-side events.

        This is a derived value, not a financial correctness judgment.
        """

        return (
            self.gross_amount
            - self.refund_amount
            - self.fee_amount
            + self.adjustment_amount
        )


class StateReconstructor:
    """
    Reconstructs the observed financial state of an event chain.

    The reconstructor:
        - aggregates observed financial events
        - preserves event provenance
        - derives arithmetic state from observed events
        - does not infer missing events
        - does not determine financial correctness
        - does not investigate discrepancies
    """

    def reconstruct(
        self,
        chain: EventChain,
        events: list[FinancialEvent],
    ) -> ObservedFinancialState:
        """
        Reconstruct state from the supplied events.

        Only events belonging to the supplied chain are considered.
        """

        chain_event_ids = set(
            chain.event_ids
        )

        chain_events = [
            event
            for event in events
            if event.event_id in chain_event_ids
        ]

        gross_amount = Decimal("0")
        refund_amount = Decimal("0")
        fee_amount = Decimal("0")
        adjustment_amount = Decimal("0")
        settlement_amount = Decimal("0")
        bank_credit_amount = Decimal("0")

        payment_event_ids: list[str] = []
        refund_event_ids: list[str] = []
        fee_event_ids: list[str] = []
        adjustment_event_ids: list[str] = []
        settlement_event_ids: list[str] = []
        bank_event_ids: list[str] = []

        for event in chain_events:

            amount = event.amount or Decimal("0")

            if event.event_type == EventType.PAYMENT_CAPTURED:
                gross_amount += amount
                payment_event_ids.append(
                    event.event_id
                )

            elif event.event_type == EventType.REFUND_CREATED:
                refund_amount += amount
                refund_event_ids.append(
                    event.event_id
                )

            elif event.event_type == EventType.FEE_APPLIED:
                fee_amount += amount
                fee_event_ids.append(
                    event.event_id
                )

            elif event.event_type == EventType.ADJUSTMENT_APPLIED:
                adjustment_amount += amount
                adjustment_event_ids.append(
                    event.event_id
                )

            elif event.event_type in {
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
            }:
                settlement_amount += amount
                settlement_event_ids.append(
                    event.event_id
                )

            elif event.event_type == EventType.BANK_CREDIT:
                bank_credit_amount += amount
                bank_event_ids.append(
                    event.event_id
                )

        return ObservedFinancialState(
            chain_id=chain.chain_id,
            gross_amount=gross_amount,
            refund_amount=refund_amount,
            fee_amount=fee_amount,
            adjustment_amount=adjustment_amount,
            settlement_amount=settlement_amount,
            bank_credit_amount=bank_credit_amount,
            payment_event_ids=tuple(
                payment_event_ids
            ),
            refund_event_ids=tuple(
                refund_event_ids
            ),
            fee_event_ids=tuple(
                fee_event_ids
            ),
            adjustment_event_ids=tuple(
                adjustment_event_ids
            ),
            settlement_event_ids=tuple(
                settlement_event_ids
            ),
            bank_event_ids=tuple(
                bank_event_ids
            ),
        )