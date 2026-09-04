import pytest

from app.evidence.graph import (
    EvidenceGraph,
)


def make_record(
    evidence_id: str,
):
    return {
        "evidence_id": evidence_id,
    }


def test_add_node():

    graph = EvidenceGraph()

    graph.add_node(
        evidence_id="EVIDENCE_001",
        record_type="payment",
        record=make_record(
            "EVIDENCE_001"
        ),
    )

    assert graph.node_count == 1

    node = graph.get_node(
        "EVIDENCE_001"
    )

    assert node is not None
    assert node.evidence_id == "EVIDENCE_001"
    assert node.record_type == "payment"


def test_add_edge():

    graph = EvidenceGraph()

    graph.add_node(
        "PAYMENT_001",
        "payment",
        make_record("PAYMENT_001"),
    )

    graph.add_node(
        "SETTLEMENT_001",
        "settlement",
        make_record("SETTLEMENT_001"),
    )

    graph.add_edge(
        source_id="PAYMENT_001",
        target_id="SETTLEMENT_001",
        relationship="settled_by",
    )

    assert graph.edge_count == 1

    edge = graph.edges[0]

    assert edge.source_id == "PAYMENT_001"
    assert edge.target_id == "SETTLEMENT_001"
    assert edge.relationship == "settled_by"


def test_related_nodes():

    graph = EvidenceGraph()

    graph.add_node(
        "PAYMENT_001",
        "payment",
        make_record("PAYMENT_001"),
    )

    graph.add_node(
        "SETTLEMENT_001",
        "settlement",
        make_record("SETTLEMENT_001"),
    )

    graph.add_node(
        "BANK_001",
        "bank",
        make_record("BANK_001"),
    )

    graph.add_edge(
        "PAYMENT_001",
        "SETTLEMENT_001",
        "settled_by",
    )

    graph.add_edge(
        "SETTLEMENT_001",
        "BANK_001",
        "credited_to",
    )

    related = graph.related_nodes(
        "SETTLEMENT_001"
    )

    related_ids = {
        node.evidence_id
        for node in related
    }

    assert related_ids == {
        "PAYMENT_001",
        "BANK_001",
    }


def test_unknown_source_cannot_create_edge():

    graph = EvidenceGraph()

    graph.add_node(
        "BANK_001",
        "bank",
        make_record("BANK_001"),
    )

    with pytest.raises(ValueError):

        graph.add_edge(
            "PAYMENT_001",
            "BANK_001",
            "credited_to",
        )


def test_duplicate_node_is_rejected():

    graph = EvidenceGraph()

    graph.add_node(
        "PAYMENT_001",
        "payment",
        make_record("PAYMENT_001"),
    )

    with pytest.raises(ValueError):

        graph.add_node(
            "PAYMENT_001",
            "payment",
            make_record("PAYMENT_001"),
        )


def test_relationships_for_node():

    graph = EvidenceGraph()

    graph.add_node(
        "PAYMENT_001",
        "payment",
        make_record("PAYMENT_001"),
    )

    graph.add_node(
        "SETTLEMENT_001",
        "settlement",
        make_record("SETTLEMENT_001"),
    )

    graph.add_edge(
        "PAYMENT_001",
        "SETTLEMENT_001",
        "settled_by",
    )

    relationships = graph.relationships_for(
        "PAYMENT_001"
    )

    assert len(relationships) == 1
    assert (
        relationships[0].relationship
        == "settled_by"
    )