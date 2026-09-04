from datetime import datetime
from decimal import Decimal

from app.ingestion.canonical_models import (
    CanonicalPayment,
    CanonicalSettlement,
)
from app.reconciliation.graph import (
    ReconciliationGraph,
)
from app.reconciliation.models import (
    Cardinality,
    MatchMethod,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)
from app.reconstruction.reconstructor import (
    Reconstructor,
)


def payment():

    return CanonicalPayment(
        evidence_id="payments:1:PAY_001",
        source_type="PAYMENT",
        source_file="payments.csv",
        source_row=1,
        payment_id="PAY_001",
        order_id="ORDER_001",
        amount=Decimal("50000"),
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
        gross_amount=Decimal("50000"),
        fee=Decimal("500"),
        tax=Decimal("0"),
        adjustment=Decimal("0"),
        net_amount=Decimal("49500"),
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

    payment_record = payment()
    settlement_record = settlement()

    graph.add_node(
        payment_record.evidence_id,
        payment_record,
    )

    graph.add_node(
        settlement_record.evidence_id,
        settlement_record,
    )

    graph.add_relationship(
        Relationship(
            relationship_id=(
                "REL_PAY_001_SET_001"
            ),
            source_record_id=(
                payment_record.evidence_id
            ),
            target_record_id=(
                settlement_record.evidence_id
            ),
            relationship_type=(
                RelationshipType
                .SETTLEMENT_FOR_PAYMENT
            ),
            cardinality=(
                Cardinality.ONE_TO_ONE
            ),
            method=MatchMethod.EXACT_ID,
            evidence=[
                "payment_id matches payment reference"
            ],
            status=(
                RelationshipStatus.CONFIRMED
            ),
            created_at=datetime.now(),
        )
    )

    return graph


def test_reconstructor_builds_complete_result():

    result = Reconstructor().reconstruct(
        make_graph()
    )

    assert result.event_count == 2
    assert result.chain_count == 1
    assert result.relationship_count == 1


def test_reconstructor_builds_payment_state():

    result = Reconstructor().reconstruct(
        make_graph()
    )

    assert (
        result.batch_state.total_gross_amount
        == Decimal("50000")
    )

    assert (
        result.batch_state.payment_event_count
        == 1
    )


def test_reconstructor_builds_settlement_state():

    result = Reconstructor().reconstruct(
        make_graph()
    )

    assert (
        result.batch_state.total_settlement_amount
        == Decimal("49500")
    )

    assert (
        result.batch_state.settlement_event_count
        == 1
    )


def test_reconstructor_preserves_observed_net():

    result = Reconstructor().reconstruct(
        make_graph()
    )

    assert (
        result.batch_state.total_observed_net_amount
        == Decimal("50000")
    )


def test_empty_graph_produces_empty_result():

    result = Reconstructor().reconstruct(
        ReconciliationGraph()
    )

    assert result.event_count == 0
    assert result.relationship_count == 0
    assert result.chain_count == 0
    assert result.batch_state.chain_count == 0


def test_reconstructor_does_not_modify_input_graph():

    graph = make_graph()

    nodes_before = dict(graph.nodes)
    relationships_before = list(
        graph.relationships
    )

    Reconstructor().reconstruct(graph)

    assert graph.nodes == nodes_before
    assert (
        graph.relationships
        == relationships_before
    )


def test_reconstruction_does_not_invent_missing_events():

    graph = ReconciliationGraph()

    payment_record = payment()

    graph.add_node(
        payment_record.evidence_id,
        payment_record,
    )

    result = Reconstructor().reconstruct(
        graph
    )

    assert result.event_count == 1

    assert (
        result.batch_state
        .settlement_event_count
        == 0
    )

    assert (
        result.batch_state
        .bank_event_count
        == 0
    )