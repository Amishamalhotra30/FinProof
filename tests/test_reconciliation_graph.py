from datetime import datetime
from decimal import Decimal

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


def make_relationship(
    source: str,
    target: str,
) -> Relationship:

    return Relationship(
        relationship_id=(
            f"REL_{source}_{target}"
        ),
        source_record_id=source,
        target_record_id=target,
        relationship_type=(
            RelationshipType.SETTLEMENT_FOR_PAYMENT
        ),
        cardinality=(
            Cardinality.ONE_TO_ONE
        ),
        method=MatchMethod.EXACT_ID,
        evidence=[
            "payment_id"
        ],
        status=(
            RelationshipStatus.CONFIRMED
        ),
        created_at=datetime.now(),
    )


def test_add_and_get_node():

    graph = ReconciliationGraph()

    record = {
        "payment_id": "PAY_001",
        "amount": Decimal("50000.00"),
    }

    graph.add_node(
        "PAY_001",
        record,
    )

    assert graph.node_count == 1

    assert (
        graph.get_node("PAY_001")
        == record
    )


def test_missing_node_returns_none():

    graph = ReconciliationGraph()

    assert (
        graph.get_node("PAY_UNKNOWN")
        is None
    )


def test_add_relationship():

    graph = ReconciliationGraph()

    relationship = make_relationship(
        "PAY_001",
        "SET_001",
    )

    graph.add_relationship(
        relationship
    )

    assert graph.relationship_count == 1

    assert (
        graph.relationships[0]
        == relationship
    )


def test_get_relationships_for_record():

    graph = ReconciliationGraph()

    first = make_relationship(
        "PAY_001",
        "SET_001",
    )

    second = make_relationship(
        "PAY_002",
        "SET_002",
    )

    graph.add_relationship(first)
    graph.add_relationship(second)

    relationships = (
        graph.get_relationships(
            "PAY_001"
        )
    )

    assert relationships == [first]


def test_relationships_from():

    graph = ReconciliationGraph()

    first = make_relationship(
        "PAY_001",
        "SET_001",
    )

    second = make_relationship(
        "PAY_001",
        "SET_002",
    )

    graph.add_relationship(first)
    graph.add_relationship(second)

    relationships = (
        graph.relationships_from(
            "PAY_001"
        )
    )

    assert len(relationships) == 2


def test_relationships_to():

    graph = ReconciliationGraph()

    first = make_relationship(
        "PAY_001",
        "SET_001",
    )

    second = make_relationship(
        "PAY_002",
        "SET_001",
    )

    graph.add_relationship(first)
    graph.add_relationship(second)

    relationships = (
        graph.relationships_to(
            "SET_001"
        )
    )

    assert len(relationships) == 2

    assert first in relationships
    assert second in relationships