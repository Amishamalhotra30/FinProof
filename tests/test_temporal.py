from datetime import datetime, timedelta

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.reconstruction.event_chain import EventChain
from app.verification.models import ControlStatus
from app.verification.temporal import (
    check_bank_after_settlement,
    check_chain_temporal_order,
    check_event_ordering,
    check_settlement_timing,
    run_temporal_controls,
)


def make_event(
    event_id: str,
    event_type: EventType,
    timestamp: datetime,
) -> FinancialEvent:
    return FinancialEvent(
        event_id=event_id,
        event_type=event_type,
        entity_id=event_id,
        amount=None,
        currency="INR",
        timestamp=timestamp,
        related_event_ids=[],
        source=RecordSource.PAYMENT,
        metadata={},
    )


def make_graph(
    events: list[FinancialEvent],
) -> EventGraph:
    graph = EventGraph()

    for event in events:
        graph.add_event(event)

    return graph


def test_event_ordering_passes_for_valid_relationship():
    base = datetime(2026, 8, 30, 10, 0)

    payment = make_event(
        "PAYMENT_1",
        EventType.PAYMENT_CAPTURED,
        base,
    )

    settlement = make_event(
        "SETTLEMENT_1",
        EventType.SETTLEMENT_PROCESSED,
        base + timedelta(minutes=10),
    )

    payment.related_event_ids.append(
        settlement.event_id
    )

    graph = make_graph(
        [payment, settlement]
    )

    result = check_event_ordering(graph)

    assert result.status == ControlStatus.PASS


def test_event_ordering_fails_when_target_precedes_source():
    base = datetime(2026, 8, 30, 10, 0)

    payment = make_event(
        "PAYMENT_1",
        EventType.PAYMENT_CAPTURED,
        base + timedelta(minutes=10),
    )

    settlement = make_event(
        "SETTLEMENT_1",
        EventType.SETTLEMENT_PROCESSED,
        base,
    )

    payment.related_event_ids.append(
        settlement.event_id
    )

    graph = make_graph(
        [payment, settlement]
    )

    result = check_event_ordering(graph)

    assert result.status == ControlStatus.FAIL
    assert set(result.affected_event_ids) == {
        "PAYMENT_1",
        "SETTLEMENT_1",
    }


def test_settlement_timing_passes():
    base = datetime(2026, 8, 30, 10, 0)

    payment = make_event(
        "PAYMENT_1",
        EventType.PAYMENT_CAPTURED,
        base,
    )

    settlement = make_event(
        "SETTLEMENT_1",
        EventType.SETTLEMENT_PROCESSED,
        base + timedelta(minutes=10),
    )

    settlement.related_event_ids.append(
        payment.event_id
    )

    graph = make_graph(
        [payment, settlement]
    )

    result = check_settlement_timing(graph)

    assert result.status == ControlStatus.PASS


def test_settlement_timing_fails_when_before_payment():
    base = datetime(2026, 8, 30, 10, 0)

    payment = make_event(
        "PAYMENT_1",
        EventType.PAYMENT_CAPTURED,
        base + timedelta(minutes=10),
    )

    settlement = make_event(
        "SETTLEMENT_1",
        EventType.SETTLEMENT_PROCESSED,
        base,
    )

    settlement.related_event_ids.append(
        payment.event_id
    )

    graph = make_graph(
        [payment, settlement]
    )

    result = check_settlement_timing(graph)

    assert result.status == ControlStatus.FAIL


def test_bank_after_settlement_passes():
    base = datetime(2026, 8, 30, 10, 0)

    settlement = make_event(
        "SETTLEMENT_1",
        EventType.SETTLEMENT_PROCESSED,
        base,
    )

    bank = make_event(
        "BANK_1",
        EventType.BANK_CREDIT,
        base + timedelta(minutes=10),
    )

    settlement.related_event_ids.append(
        bank.event_id
    )

    graph = make_graph(
        [settlement, bank]
    )

    result = check_bank_after_settlement(graph)

    assert result.status == ControlStatus.PASS


def test_bank_after_settlement_fails_when_bank_is_earlier():
    base = datetime(2026, 8, 30, 10, 0)

    settlement = make_event(
        "SETTLEMENT_1",
        EventType.SETTLEMENT_PROCESSED,
        base + timedelta(minutes=10),
    )

    bank = make_event(
        "BANK_1",
        EventType.BANK_CREDIT,
        base,
    )

    settlement.related_event_ids.append(
        bank.event_id
    )

    graph = make_graph(
        [settlement, bank]
    )

    result = check_bank_after_settlement(graph)

    assert result.status == ControlStatus.FAIL


def test_chain_temporal_order_passes():
    base = datetime(2026, 8, 30, 10, 0)

    first = make_event(
        "E1",
        EventType.PAYMENT_CAPTURED,
        base,
    )

    second = make_event(
        "E2",
        EventType.SETTLEMENT_PROCESSED,
        base + timedelta(minutes=10),
    )

    graph = make_graph(
        [first, second]
    )

    chain = EventChain(
        chain_id="CHAIN_1",
        event_ids=["E1", "E2"],
    )

    result = check_chain_temporal_order(
        graph,
        [chain],
    )

    assert result.status == ControlStatus.PASS


def test_chain_temporal_order_fails():
    base = datetime(2026, 8, 30, 10, 0)

    first = make_event(
        "E1",
        EventType.PAYMENT_CAPTURED,
        base,
    )

    second = make_event(
        "E2",
        EventType.SETTLEMENT_PROCESSED,
        base + timedelta(minutes=10),
    )

    graph = make_graph(
        [first, second]
    )

    chain = EventChain(
        chain_id="CHAIN_1",
        event_ids=["E2", "E1"],
    )

    result = check_chain_temporal_order(
        graph,
        [chain],
    )

    assert result.status == ControlStatus.FAIL


def test_run_temporal_controls_returns_all_controls():
    base = datetime(2026, 8, 30, 10, 0)

    payment = make_event(
        "PAYMENT_1",
        EventType.PAYMENT_CAPTURED,
        base,
    )

    settlement = make_event(
        "SETTLEMENT_1",
        EventType.SETTLEMENT_PROCESSED,
        base + timedelta(minutes=10),
    )

    bank = make_event(
        "BANK_1",
        EventType.BANK_CREDIT,
        base + timedelta(minutes=20),
    )

    payment.related_event_ids.append(
        settlement.event_id
    )

    settlement.related_event_ids.append(
        bank.event_id
    )

    graph = make_graph(
        [payment, settlement, bank]
    )

    chains = [
        EventChain(
            chain_id="CHAIN_1",
            event_ids=[
                "PAYMENT_1",
                "SETTLEMENT_1",
                "BANK_1",
            ],
        )
    ]

    results = run_temporal_controls(
        graph,
        chains,
    )

    assert len(results) == 4

    assert {
        result.control_id
        for result in results
    } == {
        "EVENT_ORDERING",
        "SETTLEMENT_TIMING",
        "BANK_AFTER_SETTLEMENT",
        "CHAIN_TEMPORAL_ORDER",
    }