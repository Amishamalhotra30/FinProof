from decimal import Decimal

from app.domain.enums import EventType
from app.domain.graph import EventGraph
from app.domain.records import (
    AdjustmentRecord,
    BankStatementLine,
    FeeRecord,
    OrderRecord,
    PaymentRecord,
    RefundRecord,
    SettlementRecord,
)


def generate_source_records(graph: EventGraph) -> dict[str, list]:
    orders: list[OrderRecord] = []
    payments: list[PaymentRecord] = []
    refunds: list[RefundRecord] = []
    fees: list[FeeRecord] = []
    adjustments: list[AdjustmentRecord] = []
    settlements: list[SettlementRecord] = []
    bank_lines: list[BankStatementLine] = []

    # ---------------------------------------------------------
    # PASS 1:
    # Collect financial information needed by later records.
    # ---------------------------------------------------------

    payment_amounts: dict[str, Decimal] = {}
    fee_amounts: dict[str, Decimal] = {}
    refund_amounts: dict[str, Decimal] = {}
    adjustment_amounts: dict[str, Decimal] = {}

    for event in graph.ordered_events():

        if event.event_type == EventType.PAYMENT_CAPTURED:
            payment_amounts[event.entity_id] = (
                event.amount or Decimal("0")
            )

        elif event.event_type == EventType.FEE_APPLIED:
            fee_amounts[event.entity_id] = (
                fee_amounts.get(event.entity_id, Decimal("0"))
                + (event.amount or Decimal("0"))
            )

        elif event.event_type == EventType.REFUND_CREATED:
            refund_amounts[event.entity_id] = (
                refund_amounts.get(event.entity_id, Decimal("0"))
                + (event.amount or Decimal("0"))
            )

        elif event.event_type == EventType.ADJUSTMENT_APPLIED:
            adjustment_amounts[event.entity_id] = (
                adjustment_amounts.get(event.entity_id, Decimal("0"))
                + (event.amount or Decimal("0"))
            )

    # ---------------------------------------------------------
    # PASS 2:
    # Convert events into source-system records.
    # ---------------------------------------------------------

    for event in graph.ordered_events():

        if event.event_type == EventType.ORDER_CREATED:
            orders.append(
                OrderRecord(
                    order_id=event.entity_id,
                    customer_id=event.metadata.get(
                        "customer_id",
                        "CUSTOMER_UNKNOWN",
                    ),
                    amount=event.amount or Decimal("0"),
                    currency=event.currency,
                    timestamp=event.timestamp,
                    payment_id=event.metadata.get("payment_id"),
                    status="CREATED",
                )
            )

        elif event.event_type == EventType.PAYMENT_CAPTURED:
            payments.append(
                PaymentRecord(
                    payment_id=event.entity_id,
                    order_id=event.metadata.get(
                        "order_id",
                        "ORDER_UNKNOWN",
                    ),
                    amount=event.amount or Decimal("0"),
                    status="CAPTURED",
                    captured_at=event.timestamp,
                    method=event.metadata.get(
                        "method",
                        "UPI",
                    ),
                )
            )

        elif event.event_type == EventType.REFUND_CREATED:
            refunds.append(
                RefundRecord(
                    refund_id=event.event_id,
                    payment_id=event.entity_id,
                    amount=event.amount or Decimal("0"),
                    timestamp=event.timestamp,
                    reference=event.metadata.get("reference"),
                    status="PROCESSED",
                )
            )

        elif event.event_type == EventType.FEE_APPLIED:
            fees.append(
                FeeRecord(
                    fee_id=event.event_id,
                    payment_id=event.entity_id,
                    amount=event.amount or Decimal("0"),
                    timestamp=event.timestamp,
                    status="APPLIED",
                )
            )

        elif event.event_type == EventType.ADJUSTMENT_APPLIED:
            adjustments.append(
                AdjustmentRecord(
                    event_id=event.event_id,
                    payment_id=event.entity_id,
                    event_type=event.event_type.value,
                    amount=event.amount or Decimal("0"),
                    timestamp=event.timestamp,
                    reference=event.metadata.get("reference"),
                    status="APPLIED",
                )
            )

        elif event.event_type == EventType.SETTLEMENT_CREATED:
            payment_id = event.entity_id

            gross_amount = payment_amounts.get(
                payment_id,
                Decimal("0"),
            )

            fee_amount = fee_amounts.get(
                payment_id,
                Decimal("0"),
            )

            adjustment_amount = adjustment_amounts.get(
                payment_id,
                Decimal("0"),
            )

            settlements.append(
                SettlementRecord(
                    settlement_id=event.event_id,
                    payment_id=payment_id,
                    reference=event.metadata.get(
                        "reference",
                        event.event_id,
                    ),
                    gross_amount=gross_amount,
                    fee=fee_amount,
                    tax=Decimal("0.00"),
                    adjustment=adjustment_amount,
                    net_amount=event.amount or Decimal("0"),
                    status="CREATED",
                    settled_at=event.timestamp,
                    utr=event.metadata.get("utr"),
                )
            )

        elif event.event_type == EventType.BANK_CREDIT:
            bank_lines.append(
                BankStatementLine(
                    bank_txn_id=event.event_id,
                    value_date=event.timestamp,
                    narration=event.metadata.get(
                        "narration",
                        "Settlement credit",
                    ),
                    credit=event.amount or Decimal("0"),
                    debit=Decimal("0"),
                    utr=event.metadata.get("utr"),
                    balance=Decimal("0"),
                )
            )

    return {
        "orders": orders,
        "payments": payments,
        "refunds": refunds,
        "fees": fees,
        "adjustments": adjustments,
        "settlements": settlements,
        "bank": bank_lines,
    }