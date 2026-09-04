from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType
from app.ingestion.canonical_models import (
    CanonicalPayment,
    CanonicalSettlement,
)
from app.reconciliation.graph import ReconciliationGraph
from app.reconciliation.models import (
    Cardinality,
    MatchMethod,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)
from app.reconstruction.event_graph_builder import (
    EventGraphBuilder,
)


def payment():

    return CanonicalPayment(
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


def settlement():

    return CanonicalSettlement(
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


def make_graph():

    graph = ReconciliationGraph()

    graph.add_node(
        payment().evidence_id,
        payment(),
    )

    graph.add_node(
        settlement().evidence_id,
        settlement(),
    )

    graph.add_relationship(
        Relationship(
            relationship_id=(
                "REL_PAY_001_SET_001"
            ),
            source_record_id=(
                payment().evidence_id
            ),
            target_record_id=(
                settlement().evidence_id
            ),
            relationship_type=(
                RelationshipType
                .SETTLEMENT_FOR_PAYMENT
            ),
            cardinality=(
                Cardinality.ONE_TO_ONE
            ),
            method=(
                MatchMethod.EXACT_ID
            ),
            evidence=[
                "payment_id matches payment_ref"
            ],
            status=(
                RelationshipStatus.CONFIRMED
            ),
            created_at=datetime.now(),
        )
    )

    return graph


def test_builds_events_from_reconciliation_nodes():

    result = EventGraphBuilder().build(
        make_graph()
    )

    assert result.node_count == 2

    assert (
        result.get_event(
            "payments:1:PAY_001"
        ).event_type
        == EventType.PAYMENT_CAPTURED
    )

    assert (
        result.get_event(
            "settlements:1:SET_001"
        ).event_type
        == EventType.SETTLEMENT_CREATED
    )


def test_projects_relationship_into_event_graph():

    result = EventGraphBuilder().build(
        make_graph()
    )

    payment_event = result.get_event(
        "payments:1:PAY_001"
    )

    assert (
        "settlements:1:SET_001"
        in payment_event.related_event_ids
    )


def test_event_graph_preserves_relationship_direction():

    result = EventGraphBuilder().build(
        make_graph()
    )

    payment_relationships = (
        result.get_event(
            "payments:1:PAY_001"
        ).related_event_ids
    )

    settlement_relationships = (
        result.get_event(
            "settlements:1:SET_001"
        ).related_event_ids
    )

    assert (
        "settlements:1:SET_001"
        in payment_relationships
    )

    assert (
        "payments:1:PAY_001"
        not in settlement_relationships
    )


def test_build_reconstructed_events():

    result = (
        EventGraphBuilder()
        .build_reconstructed_events(
            make_graph()
        )
    )

    assert len(result) == 2

    assert {
        event.event_type
        for event in result
    } == {
        EventType.PAYMENT_CAPTURED,
        EventType.SETTLEMENT_CREATED,
    }


def test_relationship_metadata_is_not_financial_judgment():

    result = EventGraphBuilder().build(
        make_graph()
    )

    payment_event = result.get_event(
        "payments:1:PAY_001"
    )

    assert (
        payment_event.metadata[
            "timestamp_type"
        ]
        == "CAPTURED_AT"
    )

    assert (
        "49500.00"
        not in payment_event.metadata
    )