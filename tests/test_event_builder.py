from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType
from app.ingestion.canonical_models import (
    CanonicalBankEntry,
    CanonicalFee,
    CanonicalOrder,
    CanonicalPayment,
    CanonicalRefund,
    CanonicalSettlement,
)
from app.reconstruction.event_builder import EventBuilder
from app.reconstruction.models import TimestampType


def test_build_payment_event():

    record = CanonicalPayment(
        evidence_id="payments:1:PAY_001",
        source_type="PAYMENT",
        source_file="payments.csv",
        source_row=1,
        payment_id="PAY_001",
        order_id="ORDER_001",
        amount=Decimal("50000.00"),
        currency="INR",
        event_timestamp=datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
        status="CAPTURED",
    )

    event = EventBuilder().build_payment(record)

    assert event.event_id == record.evidence_id
    assert event.event_type == EventType.PAYMENT_CAPTURED
    assert event.amount == Decimal("50000.00")
    assert event.timestamp_type == TimestampType.CAPTURED_AT
    assert event.source_evidence_ids == [
        record.evidence_id
    ]


def test_build_settlement_preserves_observed_components():

    record = CanonicalSettlement(
        evidence_id="settlements:1:SET_001",
        source_type="SETTLEMENT",
        source_file="settlements.csv",
        source_row=1,
        settlement_id="SET_001",
        payment_id="PAY_001",
        reference="PAY_001",
        gross_amount=Decimal("50000.00"),
        fee=Decimal("500.00"),
        tax=Decimal("0.00"),
        adjustment=Decimal("0.00"),
        net_amount=Decimal("49500.00"),
        event_timestamp=datetime(
            2026,
            8,
            31,
            12,
            0,
        ),
        status="CREATED",
        utr="UTR001",
    )

    event = EventBuilder().build_settlement(record)

    assert (
        event.event_type
        == EventType.SETTLEMENT_CREATED
    )

    assert event.amount == Decimal("49500.00")

    assert (
        event.attributes["gross_amount"]
        == "50000.00"
    )

    assert (
        event.attributes["fee"]
        == "500.00"
    )

    assert (
        event.attributes["net_amount"]
        == "49500.00"
    )


def test_build_bank_uses_credit_as_observed_amount():

    record = CanonicalBankEntry(
        evidence_id="bank:1:BANK_001",
        source_type="BANK",
        source_file="bank.csv",
        source_row=1,
        transaction_id="BANK_001",
        narration="Settlement credit",
        normalized_narration="SETTLEMENT CREDIT",
        credit=Decimal("49500.00"),
        debit=Decimal("0.00"),
        event_timestamp=datetime(
            2026,
            8,
            31,
            12,
            15,
        ),
        currency="INR",
        utr="UTR001",
    )

    event = EventBuilder().build_bank(record)

    assert event.event_type == EventType.BANK_CREDIT
    assert event.amount == Decimal("49500.00")
    assert event.timestamp_type == TimestampType.VALUE_DATE


def test_build_collection_ignores_unsupported_records():

    events = EventBuilder().build(
        [
            object(),
        ]
    )

    assert events == []


def test_build_all_supported_record_types():

    timestamp = datetime(
        2026,
        8,
        31,
        10,
        0,
    )

    records = [
        CanonicalOrder(
            evidence_id="orders:1:ORDER_001",
            source_type="ORDER",
            source_file="orders.csv",
            source_row=1,
            order_id="ORDER_001",
            customer_id="CUST_001",
            amount=Decimal("50000.00"),
            currency="INR",
            event_timestamp=timestamp,
            status="CREATED",
        ),
        CanonicalPayment(
            evidence_id="payments:1:PAY_001",
            source_type="PAYMENT",
            source_file="payments.csv",
            source_row=1,
            payment_id="PAY_001",
            order_id="ORDER_001",
            amount=Decimal("50000.00"),
            currency="INR",
            event_timestamp=timestamp,
            status="CAPTURED",
        ),
        CanonicalRefund(
            evidence_id="refunds:1:REF_001",
            source_type="REFUND",
            source_file="refunds.csv",
            source_row=1,
            refund_id="REF_001",
            payment_id="PAY_001",
            amount=Decimal("1000.00"),
            currency="INR",
            event_timestamp=timestamp,
            status="CREATED",
        ),
        CanonicalFee(
            evidence_id="fees:1:FEE_001",
            source_type="FEE",
            source_file="fees.csv",
            source_row=1,
            fee_id="FEE_001",
            payment_id="PAY_001",
            amount=Decimal("500.00"),
            currency="INR",
            event_timestamp=timestamp,
            status="APPLIED",
        ),
    ]

    events = EventBuilder().build(records)

    assert len(events) == 4

    assert {
        event.event_type
        for event in events
    } == {
        EventType.ORDER_CREATED,
        EventType.PAYMENT_CAPTURED,
        EventType.REFUND_CREATED,
        EventType.FEE_APPLIED,
    }