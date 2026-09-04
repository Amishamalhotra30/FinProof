from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.reconstruction.event_chain import (
    EventChainBuilder,
)


def make_event(
    event_id: str,
    event_type: EventType,
    timestamp: datetime,
) -> FinancialEvent:

    return FinancialEvent(
        event_id=event_id,
        event_type=event_type,
        entity_id="PAY_001",
        amount=Decimal("100.00"),
        currency="INR",
        timestamp=timestamp,
        source=RecordSource.PAYMENT,
    )


def build_linear_graph():

    order = make_event(
        "ORDER",
        EventType.ORDER_CREATED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        datetime(
            2026,
            8,
            31,
            10,
            5,
        ),
    )

    settlement = make_event(
        "SETTLEMENT",
        EventType.SETTLEMENT_CREATED,
        datetime(
            2026,
            8,
            31,
            12,
            0,
        ),
    )

    bank = make_event(
        "BANK",
        EventType.BANK_CREDIT,
        datetime(
            2026,
            8,
            31,
            12,
            15,
        ),
    )

    graph = EventGraph()

    for event in (
        order,
        payment,
        settlement,
        bank,
    ):
        graph.add_event(event)

    graph.add_relationship(
        "ORDER",
        "PAYMENT",
    )

    graph.add_relationship(
        "PAYMENT",
        "SETTLEMENT",
    )

    graph.add_relationship(
        "SETTLEMENT",
        "BANK",
    )

    return graph


def test_linear_events_form_one_chain():

    graph = build_linear_graph()

    chains = EventChainBuilder().build(
        graph
    )

    assert len(chains) == 1

    assert chains[0].event_ids == [
        "ORDER",
        "PAYMENT",
        "SETTLEMENT",
        "BANK",
    ]


def test_chain_is_temporally_ordered():

    graph = build_linear_graph()

    # Inserted in a deliberately non-chronological order.
    unordered = EventGraph()

    for event_id in (
        "BANK",
        "SETTLEMENT",
        "ORDER",
        "PAYMENT",
    ):
        unordered.add_event(
            graph.get_event(event_id)
        )

    unordered.add_relationship(
        "ORDER",
        "PAYMENT",
    )

    unordered.add_relationship(
        "PAYMENT",
        "SETTLEMENT",
    )

    unordered.add_relationship(
        "SETTLEMENT",
        "BANK",
    )

    chains = EventChainBuilder().build(
        unordered
    )

    assert chains[0].event_ids == [
        "ORDER",
        "PAYMENT",
        "SETTLEMENT",
        "BANK",
    ]


def test_disconnected_events_remain_separate():

    first = make_event(
        "EVENT_A",
        EventType.PAYMENT_CAPTURED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    second = make_event(
        "EVENT_B",
        EventType.BANK_CREDIT,
        datetime(
            2026,
            8,
            31,
            11,
            0,
        ),
    )

    graph = EventGraph()

    graph.add_event(first)
    graph.add_event(second)

    chains = EventChainBuilder().build(
        graph
    )

    assert len(chains) == 2

    assert {
        tuple(chain.event_ids)
        for chain in chains
    } == {
        ("EVENT_A",),
        ("EVENT_B",),
    }


def test_branching_events_stay_in_same_component():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    refund = make_event(
        "REFUND",
        EventType.REFUND_CREATED,
        datetime(
            2026,
            8,
            31,
            11,
            0,
        ),
    )

    fee = make_event(
        "FEE",
        EventType.FEE_APPLIED,
        datetime(
            2026,
            8,
            31,
            11,
            5,
        ),
    )

    graph = EventGraph()

    graph.add_event(payment)
    graph.add_event(refund)
    graph.add_event(fee)

    graph.add_relationship(
        "PAYMENT",
        "REFUND",
    )

    graph.add_relationship(
        "PAYMENT",
        "FEE",
    )

    chains = EventChainBuilder().build(
        graph
    )

    assert len(chains) == 1

    assert chains[0].event_ids == [
        "PAYMENT",
        "REFUND",
        "FEE",
    ]


def test_reverse_relationship_still_belongs_to_same_chain():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    settlement = make_event(
        "SETTLEMENT",
        EventType.SETTLEMENT_CREATED,
        datetime(
            2026,
            8,
            31,
            12,
            0,
        ),
    )

    graph = EventGraph()

    graph.add_event(payment)
    graph.add_event(settlement)

    graph.add_relationship(
        "SETTLEMENT",
        "PAYMENT",
    )

    chains = EventChainBuilder().build(
        graph
    )

    assert len(chains) == 1

    assert set(
        chains[0].event_ids
    ) == {
        "PAYMENT",
        "SETTLEMENT",
    }


def test_missing_event_is_not_invented():

    payment = make_event(
        "PAYMENT",
        EventType.PAYMENT_CAPTURED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    bank = make_event(
        "BANK",
        EventType.BANK_CREDIT,
        datetime(
            2026,
            8,
            31,
            12,
            0,
        ),
    )

    graph = EventGraph()

    graph.add_event(payment)
    graph.add_event(bank)

    graph.add_relationship(
        "PAYMENT",
        "BANK",
    )

    chains = EventChainBuilder().build(
        graph
    )

    assert len(chains) == 1

    assert chains[0].event_ids == [
        "PAYMENT",
        "BANK",
    ]

    assert all(
        event_id in graph.events
        for event_id in chains[0].event_ids
    )


def test_chain_metadata():

    graph = build_linear_graph()

    chain = EventChainBuilder().build(
        graph
    )[0]

    assert chain.first_event_id == "ORDER"
    assert chain.last_event_id == "BANK"
    assert chain.length == 4
    assert chain.chain_id.startswith(
        "CHAIN_"
    )


def test_build_event_sequences():

    graph = build_linear_graph()

    sequences = (
        EventChainBuilder()
        .build_event_sequences(graph)
    )

    assert len(sequences) == 1

    assert [
        event.event_id
        for event in sequences[0]
    ] == [
        "ORDER",
        "PAYMENT",
        "SETTLEMENT",
        "BANK",
    ]