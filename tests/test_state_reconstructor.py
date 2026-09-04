from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.reconstruction.event_chain import EventChain
from app.reconstruction.state_reconstructor import (
    StateReconstructor,
)


def make_event(
    event_id: str,
    event_type: EventType,
    amount: str,
) -> FinancialEvent:

    return FinancialEvent(
        event_id=event_id,
        event_type=event_type,
        entity_id="PAY_001",
        amount=Decimal(amount),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
        source=RecordSource.PAYMENT,
    )


def make_chain(
    *event_ids: str,
) -> EventChain:

    return EventChain(
        chain_id="CHAIN_001",
        event_ids=list(event_ids),
    )


def test_reconstructs_payment_amount():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        "50000.00",
    )

    chain = make_chain(
        "PAYMENT"
    )

    state = StateReconstructor().reconstruct(
        chain,
        [payment],
    )

    assert state.gross_amount == Decimal(
        "50000.00"
    )

    assert state.payment_event_ids == (
        "PAYMENT",
    )


def test_reconstructs_refunds_and_fees():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        "50000.00",
    )

    refund = make_event(
        "REFUND",
        EventType.REFUND_CREATED,
        "5000.00",
    )

    fee = make_event(
        "FEE",
        EventType.FEE_APPLIED,
        "500.00",
    )

    chain = make_chain(
        "PAYMENT",
        "REFUND",
        "FEE",
    )

    state = StateReconstructor().reconstruct(
        chain,
        [
            payment,
            refund,
            fee,
        ],
    )

    assert state.gross_amount == Decimal(
        "50000.00"
    )

    assert state.refund_amount == Decimal(
        "5000.00"
    )

    assert state.fee_amount == Decimal(
        "500.00"
    )

    assert state.observed_net_amount == Decimal(
        "44500.00"
    )


def test_reconstructs_adjustments():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        "50000.00",
    )

    adjustment = make_event(
        "ADJUSTMENT",
        EventType.ADJUSTMENT_APPLIED,
        "250.00",
    )

    chain = make_chain(
        "PAYMENT",
        "ADJUSTMENT",
    )

    state = StateReconstructor().reconstruct(
        chain,
        [
            payment,
            adjustment,
        ],
    )

    assert state.adjustment_amount == Decimal(
        "250.00"
    )

    assert state.observed_net_amount == Decimal(
        "50250.00"
    )


def test_reconstructs_settlement_and_bank_amounts():

    settlement = make_event(
        "SETTLEMENT",
        EventType.SETTLEMENT_PROCESSED,
        "49500.00",
    )

    bank = make_event(
        "BANK",
        EventType.BANK_CREDIT,
        "49500.00",
    )

    chain = make_chain(
        "SETTLEMENT",
        "BANK",
    )

    state = StateReconstructor().reconstruct(
        chain,
        [
            settlement,
            bank,
        ],
    )

    assert state.settlement_amount == Decimal(
        "49500.00"
    )

    assert state.bank_credit_amount == Decimal(
        "49500.00"
    )

    assert state.settlement_event_ids == (
        "SETTLEMENT",
    )

    assert state.bank_event_ids == (
        "BANK",
    )


def test_multiple_refunds_are_aggregated():

    refund_one = make_event(
        "REFUND_1",
        EventType.REFUND_CREATED,
        "1000.00",
    )

    refund_two = make_event(
        "REFUND_2",
        EventType.REFUND_CREATED,
        "1500.00",
    )

    chain = make_chain(
        "REFUND_1",
        "REFUND_2",
    )

    state = StateReconstructor().reconstruct(
        chain,
        [
            refund_one,
            refund_two,
        ],
    )

    assert state.refund_amount == Decimal(
        "2500.00"
    )

    assert state.refund_event_ids == (
        "REFUND_1",
        "REFUND_2",
    )


def test_events_outside_chain_are_ignored():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        "50000.00",
    )

    unrelated = make_event(
        "OTHER_PAYMENT",
        EventType.PAYMENT_CAPTURED,
        "99999.00",
    )

    chain = make_chain(
        "PAYMENT"
    )

    state = StateReconstructor().reconstruct(
        chain,
        [
            payment,
            unrelated,
        ],
    )

    assert state.gross_amount == Decimal(
        "50000.00"
    )


def test_missing_event_is_not_created():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        "50000.00",
    )

    bank = make_event(
        "BANK",
        EventType.BANK_CREDIT,
        "49500.00",
    )

    chain = make_chain(
        "PAYMENT",
        "BANK",
    )

    state = StateReconstructor().reconstruct(
        chain,
        [
            payment,
            bank,
        ],
    )

    assert state.gross_amount == Decimal(
        "50000.00"
    )

    assert state.settlement_amount == Decimal(
        "0"
    )

    assert state.bank_credit_amount == Decimal(
        "49500.00"
    )

    assert state.settlement_event_ids == ()


def test_empty_chain_produces_zero_state():

    chain = make_chain()

    state = StateReconstructor().reconstruct(
        chain,
        [],
    )

    assert state.gross_amount == Decimal("0")
    assert state.refund_amount == Decimal("0")
    assert state.fee_amount == Decimal("0")
    assert state.adjustment_amount == Decimal("0")
    assert state.settlement_amount == Decimal("0")
    assert state.bank_credit_amount == Decimal("0")
    assert state.observed_net_amount == Decimal("0")


def test_state_preserves_chain_id():

    chain = EventChain(
        chain_id="CHAIN_SPECIAL",
        event_ids=[],
    )

    state = StateReconstructor().reconstruct(
        chain,
        [],
    )

    assert state.chain_id == "CHAIN_SPECIAL"