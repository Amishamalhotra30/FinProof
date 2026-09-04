from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.verification.duplicates import (
    check_duplicate_events,
    run_duplicate_controls,
)
from app.verification.models import (
    ControlStatus,
)


def make_event(
    event_id: str,
    amount: str = "50000.00",
) -> FinancialEvent:
    return FinancialEvent(
        event_id=event_id,
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id="PAYMENT_001",
        amount=Decimal(amount),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            30,
            10,
            0,
        ),
        related_event_ids=[],
        source=RecordSource.PAYMENT,
        metadata={},
    )


def test_duplicate_events_fail():
    graph = EventGraph()

    graph.add_event(
        make_event("PAYMENT_001")
    )

    graph.add_event(
        make_event("PAYMENT_001_DUP")
    )

    result = check_duplicate_events(
        graph
    )

    assert result.status == ControlStatus.FAIL

    assert set(
        result.affected_event_ids
    ) == {
        "PAYMENT_001",
        "PAYMENT_001_DUP",
    }

    assert result.blocking is True


def test_distinct_events_pass():
    graph = EventGraph()

    graph.add_event(
        make_event(
            "PAYMENT_001",
            "50000.00",
        )
    )

    graph.add_event(
        make_event(
            "PAYMENT_002",
            "60000.00",
        )
    )

    result = check_duplicate_events(
        graph
    )

    assert result.status == ControlStatus.PASS
    assert result.affected_event_ids == []
    assert result.blocking is False


def test_different_entity_is_not_duplicate():
    graph = EventGraph()

    first = make_event(
        "PAYMENT_001"
    )

    second = make_event(
        "PAYMENT_002"
    )

    second.entity_id = "PAYMENT_002"

    graph.add_event(first)
    graph.add_event(second)

    result = check_duplicate_events(
        graph
    )

    assert result.status == ControlStatus.PASS


def test_different_timestamp_is_not_duplicate():
    graph = EventGraph()

    first = make_event(
        "PAYMENT_001"
    )

    second = make_event(
        "PAYMENT_002"
    )

    second.timestamp = datetime(
        2026,
        8,
        30,
        10,
        1,
    )

    graph.add_event(first)
    graph.add_event(second)

    result = check_duplicate_events(
        graph
    )

    assert result.status == ControlStatus.PASS


def test_duplicate_control_does_not_modify_graph():
    graph = EventGraph()

    first = make_event(
        "PAYMENT_001"
    )

    second = make_event(
        "PAYMENT_001_DUP"
    )

    graph.add_event(first)
    graph.add_event(second)

    before_ids = list(
        graph.events.keys()
    )

    before_count = graph.node_count

    check_duplicate_events(
        graph
    )

    assert list(
        graph.events.keys()
    ) == before_ids

    assert graph.node_count == before_count


def test_run_duplicate_controls_returns_all_controls():
    graph = EventGraph()

    graph.add_event(
        make_event("PAYMENT_001")
    )

    results = run_duplicate_controls(
        graph
    )

    assert len(results) == 1

    assert results[0].control_id == (
        "DUPLICATE_EVENT"
    )