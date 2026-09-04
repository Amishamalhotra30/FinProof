from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.reconstruction.models import TimestampType
from app.reconstruction.temporal_orderer import (
    TemporalOrderer,
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
        metadata={
            "timestamp_type": (
                TimestampType.CAPTURED_AT.value
            )
        },
    )


def test_events_are_ordered_chronologically():

    late = make_event(
        "EVENT_003",
        EventType.BANK_CREDIT,
        datetime(
            2026,
            8,
            31,
            12,
            15,
        ),
    )

    early = make_event(
        "EVENT_001",
        EventType.ORDER_CREATED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    middle = make_event(
        "EVENT_002",
        EventType.PAYMENT_CAPTURED,
        datetime(
            2026,
            8,
            31,
            10,
            5,
        ),
    )

    result = TemporalOrderer().order(
        [late, early, middle]
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "EVENT_001",
        "EVENT_002",
        "EVENT_003",
    ]


def test_equal_timestamps_have_deterministic_order():

    second = make_event(
        "EVENT_B",
        EventType.PAYMENT_CAPTURED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    first = make_event(
        "EVENT_A",
        EventType.ORDER_CREATED,
        datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
    )

    result = TemporalOrderer().order(
        [second, first]
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "EVENT_A",
        "EVENT_B",
    ]


def test_order_does_not_modify_original_list():

    first = make_event(
        "EVENT_001",
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
        "EVENT_002",
        EventType.BANK_CREDIT,
        datetime(
            2026,
            8,
            31,
            12,
            0,
        ),
    )

    original = [
        second,
        first,
    ]

    result = TemporalOrderer().order(
        original
    )

    assert original == [
        second,
        first,
    ]

    assert result == [
        first,
        second,
    ]


def test_graph_ordering_does_not_modify_graph():

    first = make_event(
        "EVENT_001",
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
        "EVENT_002",
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

    graph.add_event(second)
    graph.add_event(first)

    before = list(
        graph.events.keys()
    )

    result = TemporalOrderer().order_graph(
        graph
    )

    assert [
        event.event_id
        for event in result
    ] == [
        "EVENT_001",
        "EVENT_002",
    ]

    assert list(
        graph.events.keys()
    ) == before