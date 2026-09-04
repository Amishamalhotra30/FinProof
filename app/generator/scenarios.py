from datetime import datetime, timedelta
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph


def generate_normal_settlement(
    case_id: str,
    base_time: datetime,
    payment_amount: Decimal = Decimal("50000.00"),
    refund_amount: Decimal = Decimal("5000.00"),
    fee_amount: Decimal = Decimal("1000.00"),
) -> EventGraph:
    """
    Generate a financially consistent normal-settlement case.

    Financial invariant:

        settlement = payment - refund - fee
    """

    if payment_amount <= Decimal("0"):
        raise ValueError("payment_amount must be positive")

    if refund_amount < Decimal("0"):
        raise ValueError("refund_amount cannot be negative")

    if fee_amount < Decimal("0"):
        raise ValueError("fee_amount cannot be negative")

    if refund_amount + fee_amount > payment_amount:
        raise ValueError(
            "refund_amount + fee_amount cannot exceed payment_amount"
        )

    settlement_amount = (
        payment_amount
        - refund_amount
        - fee_amount
    )

    graph = EventGraph()

    order = FinancialEvent(
        event_id=f"{case_id}_ORDER_EVENT",
        event_type=EventType.ORDER_CREATED,
        entity_id=f"{case_id}_ORDER",
        amount=payment_amount,
        currency="INR",
        timestamp=base_time,
        source=RecordSource.ORDER,
        metadata={
            "customer_id": f"{case_id}_CUSTOMER",
            "payment_id": f"{case_id}_PAYMENT",
        },
    )

    payment = FinancialEvent(
        event_id=f"{case_id}_PAYMENT_EVENT",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id=f"{case_id}_PAYMENT",
        amount=payment_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=2),
        source=RecordSource.PAYMENT,
        metadata={
            "order_id": f"{case_id}_ORDER",
            "method": "UPI",
        },
    )

    fee = FinancialEvent(
        event_id=f"{case_id}_FEE_EVENT",
        event_type=EventType.FEE_APPLIED,
        entity_id=f"{case_id}_PAYMENT",
        amount=fee_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=3),
        source=RecordSource.FEE,
    )

    refund = FinancialEvent(
        event_id=f"{case_id}_REFUND_EVENT",
        event_type=EventType.REFUND_CREATED,
        entity_id=f"{case_id}_PAYMENT",
        amount=refund_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=4),
        source=RecordSource.REFUND,
        metadata={
            "reference": f"REF-{case_id}",
        },
    )

    settlement = FinancialEvent(
        event_id=f"{case_id}_SETTLEMENT_EVENT",
        event_type=EventType.SETTLEMENT_CREATED,
        entity_id=f"{case_id}_PAYMENT",
        amount=settlement_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=10),
        source=RecordSource.SETTLEMENT,
        metadata={
            "reference": f"SET-{case_id}",
            "utr": f"UTR{case_id.replace('_', '')}",
        },
    )

    bank_credit = FinancialEvent(
        event_id=f"{case_id}_BANK_EVENT",
        event_type=EventType.BANK_CREDIT,
        entity_id=f"{case_id}_PAYMENT",
        amount=settlement_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=15),
        source=RecordSource.BANK,
        metadata={
            "utr": f"UTR{case_id.replace('_', '')}",
            "narration": f"Settlement credit {case_id}",
        },
    )

    graph.add_event(order)
    graph.add_event(payment)
    graph.add_event(fee)
    graph.add_event(refund)
    graph.add_event(settlement)
    graph.add_event(bank_credit)

    graph.add_relationship(
        order.event_id,
        payment.event_id,
    )

    graph.add_relationship(
        payment.event_id,
        fee.event_id,
    )

    graph.add_relationship(
        payment.event_id,
        refund.event_id,
    )

    graph.add_relationship(
        payment.event_id,
        settlement.event_id,
    )

    graph.add_relationship(
        settlement.event_id,
        bank_credit.event_id,
    )

    return graph
def generate_partial_refund(
    case_id: str,
    base_time: datetime,
    payment_amount: Decimal,
    refund_amount: Decimal,
    fee_amount: Decimal,
) -> EventGraph:
    if refund_amount <= Decimal("0"):
        raise ValueError("refund_amount must be positive")

    if refund_amount >= payment_amount:
        raise ValueError(
            "partial refund must be less than payment amount"
        )

    if fee_amount < Decimal("0"):
        raise ValueError("fee_amount cannot be negative")

    if refund_amount + fee_amount >= payment_amount:
        raise ValueError(
            "refund_amount + fee_amount must be less than payment_amount"
        )

    return generate_normal_settlement(
        case_id=case_id,
        base_time=base_time,
        payment_amount=payment_amount,
        refund_amount=refund_amount,
        fee_amount=fee_amount,
    )
def generate_split_settlement(
    case_id: str,
    base_time: datetime,
    payment_amount: Decimal,
    refund_amount: Decimal,
    fee_amount: Decimal,
) -> EventGraph:
    if payment_amount <= Decimal("0"):
        raise ValueError("payment_amount must be positive")

    if refund_amount < Decimal("0"):
        raise ValueError("refund_amount cannot be negative")

    if fee_amount < Decimal("0"):
        raise ValueError("fee_amount cannot be negative")

    if refund_amount + fee_amount >= payment_amount:
        raise ValueError(
            "refund_amount + fee_amount must be less than payment_amount"
        )

    net_amount = (
        payment_amount
        - refund_amount
        - fee_amount
    )

    # Split the net settlement into two parts.
    first_settlement = (
        net_amount * Decimal("0.60")
    ).quantize(Decimal("0.01"))

    second_settlement = (
        net_amount - first_settlement
    ).quantize(Decimal("0.01"))

    graph = EventGraph()

    order = FinancialEvent(
        event_id=f"{case_id}_ORDER_EVENT",
        event_type=EventType.ORDER_CREATED,
        entity_id=f"{case_id}_ORDER",
        amount=payment_amount,
        currency="INR",
        timestamp=base_time,
        source=RecordSource.ORDER,
        metadata={
            "customer_id": f"{case_id}_CUSTOMER",
            "payment_id": f"{case_id}_PAYMENT",
        },
    )

    payment = FinancialEvent(
        event_id=f"{case_id}_PAYMENT_EVENT",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id=f"{case_id}_PAYMENT",
        amount=payment_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=2),
        source=RecordSource.PAYMENT,
        metadata={
            "order_id": f"{case_id}_ORDER",
            "method": "UPI",
        },
    )

    fee = FinancialEvent(
        event_id=f"{case_id}_FEE_EVENT",
        event_type=EventType.FEE_APPLIED,
        entity_id=f"{case_id}_PAYMENT",
        amount=fee_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=3),
        source=RecordSource.FEE,
    )

    refund = FinancialEvent(
        event_id=f"{case_id}_REFUND_EVENT",
        event_type=EventType.REFUND_CREATED,
        entity_id=f"{case_id}_PAYMENT",
        amount=refund_amount,
        currency="INR",
        timestamp=base_time + timedelta(minutes=4),
        source=RecordSource.REFUND,
        metadata={
            "reference": f"REF-{case_id}",
        },
    )

    settlement_a = FinancialEvent(
        event_id=f"{case_id}_SETTLEMENT_A_EVENT",
        event_type=EventType.SETTLEMENT_CREATED,
        entity_id=f"{case_id}_PAYMENT",
        amount=first_settlement,
        currency="INR",
        timestamp=base_time + timedelta(minutes=10),
        source=RecordSource.SETTLEMENT,
        metadata={
            "reference": f"SET-{case_id}-A",
            "utr": f"UTR{case_id.replace('_', '')}A",
            "split_index": "A",
        },
    )

    settlement_b = FinancialEvent(
        event_id=f"{case_id}_SETTLEMENT_B_EVENT",
        event_type=EventType.SETTLEMENT_CREATED,
        entity_id=f"{case_id}_PAYMENT",
        amount=second_settlement,
        currency="INR",
        timestamp=base_time + timedelta(minutes=20),
        source=RecordSource.SETTLEMENT,
        metadata={
            "reference": f"SET-{case_id}-B",
            "utr": f"UTR{case_id.replace('_', '')}B",
            "split_index": "B",
        },
    )

    bank_a = FinancialEvent(
        event_id=f"{case_id}_BANK_A_EVENT",
        event_type=EventType.BANK_CREDIT,
        entity_id=f"{case_id}_PAYMENT",
        amount=first_settlement,
        currency="INR",
        timestamp=base_time + timedelta(minutes=15),
        source=RecordSource.BANK,
        metadata={
            "utr": f"UTR{case_id.replace('_', '')}A",
            "narration": f"Settlement credit {case_id} A",
        },
    )

    bank_b = FinancialEvent(
        event_id=f"{case_id}_BANK_B_EVENT",
        event_type=EventType.BANK_CREDIT,
        entity_id=f"{case_id}_PAYMENT",
        amount=second_settlement,
        currency="INR",
        timestamp=base_time + timedelta(minutes=25),
        source=RecordSource.BANK,
        metadata={
            "utr": f"UTR{case_id.replace('_', '')}B",
            "narration": f"Settlement credit {case_id} B",
        },
    )

    graph.add_event(order)
    graph.add_event(payment)
    graph.add_event(fee)
    graph.add_event(refund)
    graph.add_event(settlement_a)
    graph.add_event(settlement_b)
    graph.add_event(bank_a)
    graph.add_event(bank_b)

    graph.add_relationship(
        order.event_id,
        payment.event_id,
    )

    graph.add_relationship(
        payment.event_id,
        fee.event_id,
    )

    graph.add_relationship(
        payment.event_id,
        refund.event_id,
    )

    graph.add_relationship(
        payment.event_id,
        settlement_a.event_id,
    )

    graph.add_relationship(
        payment.event_id,
        settlement_b.event_id,
    )

    graph.add_relationship(
        settlement_a.event_id,
        bank_a.event_id,
    )

    graph.add_relationship(
        settlement_b.event_id,
        bank_b.event_id,
    )

    return graph