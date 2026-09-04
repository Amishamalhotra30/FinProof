from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.verification.currency import (
    check_currency_consistency,
    run_currency_controls,
)
from app.verification.models import ControlStatus


def make_event(
    event_id: str,
    currency: str = "INR",
) -> FinancialEvent:
    return FinancialEvent(
        event_id=event_id,
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id=event_id,
        amount=Decimal("50000.00"),
        currency=currency,
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


def test_currency_consistency_passes_for_single_currency():
    graph = EventGraph()

    graph.add_event(
        make_event(
            "PAYMENT_001",
            "INR",
        )
    )

    graph.add_event(
        make_event(
            "PAYMENT_002",
            "INR",
        )
    )

    result = check_currency_consistency(
        graph
    )

    assert result.status == ControlStatus.PASS
    assert result.affected_event_ids == []
    assert result.blocking is False


def test_currency_consistency_fails_for_multiple_currencies():
    graph = EventGraph()

    graph.add_event(
        make_event(
            "PAYMENT_001",
            "INR",
        )
    )

    graph.add_event(
        make_event(
            "PAYMENT_002",
            "USD",
        )
    )

    result = check_currency_consistency(
        graph
    )

    assert result.status == ControlStatus.FAIL

    assert set(
        result.affected_event_ids
    ) == {
        "PAYMENT_001",
        "PAYMENT_002",
    }

    assert result.blocking is True


def test_currency_control_does_not_convert_currency():
    graph = EventGraph()

    graph.add_event(
        make_event(
            "PAYMENT_001",
            "INR",
        )
    )

    graph.add_event(
        make_event(
            "PAYMENT_002",
            "USD",
        )
    )

    before = {
        event_id: event.currency
        for event_id, event
        in graph.events.items()
    }

    check_currency_consistency(
        graph
    )

    after = {
        event_id: event.currency
        for event_id, event
        in graph.events.items()
    }

    assert after == before


def test_currency_control_on_empty_graph_passes():
    graph = EventGraph()

    result = check_currency_consistency(
        graph
    )

    assert result.status == ControlStatus.PASS


def test_run_currency_controls_returns_expected_control():
    graph = EventGraph()

    graph.add_event(
        make_event(
            "PAYMENT_001",
            "INR",
        )
    )

    results = run_currency_controls(
        graph
    )

    assert len(results) == 1
    assert results[0].control_id == (
        "CURRENCY_CONSISTENCY"
    )