from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.domain.ground_truth import GroundTruthBatch, GroundTruthCase
from app.generator.scenarios import generate_normal_settlement


def test_financial_event_creation():
    event = FinancialEvent(
        event_id="EVT_001",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id="PAY_001",
        amount=Decimal("50000.00"),
        currency="INR",
        timestamp=datetime(2026, 8, 30, 10, 0, 0),
        source=RecordSource.PAYMENT,
    )

    assert event.event_id == "EVT_001"
    assert event.event_type == EventType.PAYMENT_CAPTURED
    assert event.amount == Decimal("50000.00")


def test_event_graph_relationship_and_ordering():
    payment = FinancialEvent(
        event_id="EVT_001",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id="PAY_001",
        amount=Decimal("50000.00"),
        currency="INR",
        timestamp=datetime(2026, 8, 30, 10, 0, 0),
        source=RecordSource.PAYMENT,
    )

    refund = FinancialEvent(
        event_id="EVT_002",
        event_type=EventType.REFUND_CREATED,
        entity_id="PAY_001",
        amount=Decimal("5000.00"),
        currency="INR",
        timestamp=datetime(2026, 8, 30, 11, 0, 0),
        source=RecordSource.REFUND,
    )

    graph = EventGraph()

    graph.add_event(payment)
    graph.add_event(refund)

    graph.add_relationship("EVT_001", "EVT_002")

    assert graph.get_event("EVT_001").related_event_ids == ["EVT_002"]

    ordered = graph.ordered_events()

    assert ordered[0].event_id == "EVT_001"
    assert ordered[1].event_id == "EVT_002"


def test_ground_truth_batch_scenario_counts():
    payment = FinancialEvent(
        event_id="EVT_001",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id="PAY_001",
        amount=Decimal("50000.00"),
        currency="INR",
        timestamp=datetime(2026, 8, 30, 10, 0, 0),
        source=RecordSource.PAYMENT,
    )

    graph = EventGraph()
    graph.add_event(payment)

    case_1 = GroundTruthCase(
        case_id="CASE_001",
        scenario="NORMAL_SETTLEMENT",
        event_graph=graph,
    )

    case_2 = GroundTruthCase(
        case_id="CASE_002",
        scenario="NORMAL_SETTLEMENT",
        event_graph=graph,
    )

    case_3 = GroundTruthCase(
        case_id="CASE_003",
        scenario="PARTIAL_REFUND",
        event_graph=graph,
    )

    batch = GroundTruthBatch(
        batch_id="batch_42",
        seed=42,
        cases=[case_1, case_2, case_3],
    )

    counts = batch.scenario_counts()

    assert counts["NORMAL_SETTLEMENT"] == 2
    assert counts["PARTIAL_REFUND"] == 1


def test_generate_normal_settlement():
    graph = generate_normal_settlement(
        case_id="CASE_001",
        base_time=datetime(2026, 8, 30, 10, 0, 0),
    )

    assert len(graph.events) == 6

    payment = graph.get_event("CASE_001_PAYMENT_EVENT")
    fee = graph.get_event("CASE_001_FEE_EVENT")
    refund = graph.get_event("CASE_001_REFUND_EVENT")
    settlement = graph.get_event("CASE_001_SETTLEMENT_EVENT")
    bank = graph.get_event("CASE_001_BANK_EVENT")

    assert payment.event_type == EventType.PAYMENT_CAPTURED
    assert payment.amount == Decimal("50000.00")

    assert fee.amount == Decimal("1000.00")
    assert refund.amount == Decimal("5000.00")

    assert settlement.amount == Decimal("44000.00")
    assert bank.amount == Decimal("44000.00")


def test_normal_settlement_relationships():
    graph = generate_normal_settlement(
        case_id="CASE_001",
        base_time=datetime(2026, 8, 30, 10, 0, 0),
    )

    payment = graph.get_event("CASE_001_PAYMENT_EVENT")
    settlement = graph.get_event("CASE_001_SETTLEMENT_EVENT")

    assert "CASE_001_FEE_EVENT" in payment.related_event_ids
    assert "CASE_001_REFUND_EVENT" in payment.related_event_ids
    assert "CASE_001_SETTLEMENT_EVENT" in payment.related_event_ids

    assert "CASE_001_BANK_EVENT" in settlement.related_event_ids

def test_normal_settlement_calculates_amounts():
    graph = generate_normal_settlement(
        case_id="CASE_002",
        base_time=datetime(2026, 8, 30, 12, 0, 0),
        payment_amount=Decimal("75000.00"),
        refund_amount=Decimal("8000.00"),
        fee_amount=Decimal("1500.00"),
    )

    payment = graph.get_event("CASE_002_PAYMENT_EVENT")
    refund = graph.get_event("CASE_002_REFUND_EVENT")
    fee = graph.get_event("CASE_002_FEE_EVENT")
    settlement = graph.get_event("CASE_002_SETTLEMENT_EVENT")
    bank = graph.get_event("CASE_002_BANK_EVENT")

    assert payment.amount == Decimal("75000.00")
    assert refund.amount == Decimal("8000.00")
    assert fee.amount == Decimal("1500.00")

    expected_settlement = (
        payment.amount
        - refund.amount
        - fee.amount
    )

    assert settlement.amount == expected_settlement
    assert bank.amount == expected_settlement
def test_normal_settlement_rejects_invalid_amounts():
    try:
        generate_normal_settlement(
            case_id="CASE_BAD",
            base_time=datetime(2026, 8, 30, 12, 0, 0),
            payment_amount=Decimal("5000.00"),
            refund_amount=Decimal("4000.00"),
            fee_amount=Decimal("2000.00"),
        )
    except ValueError as exc:
        assert "cannot exceed" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for invalid financial amounts"
        )