from app.evidence.relationship_resolver import (
    RelationshipResolver,
)
from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)


def payment():
    return {
        "payment_id": "PAY_001",
        "order_ref": "ORDER_001",
        "amount": "50000.00",
        "captured_on": "2026-08-31T10:00:00",
        "payment_status": "CAPTURED",
        "currency_code": "INR",
    }


def refund():
    return {
        "refund_id": "REFUND_001",
        "payment_ref": "PAY_001",
        "refund_amount": "1000.00",
        "created_on": "2026-08-31T11:00:00",
        "refund_status": "PROCESSED",
    }


def fee():
    return {
        "fee_id": "FEE_001",
        "payment_ref": "PAY_001",
        "fee_amount": "500.00",
        "created_on": "2026-08-31T11:00:00",
        "fee_status": "APPLIED",
    }


def test_payment_refund_relationship():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            refunds=[refund()],
        )
    )

    graph = RelationshipResolver().resolve(result)

    assert graph.node_count == 2
    assert graph.edge_count == 1

    edge = graph.edges[0]

    assert edge.relationship == "refunded_by"


def test_payment_fee_relationship():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            fees=[fee()],
        )
    )

    graph = RelationshipResolver().resolve(result)

    assert graph.node_count == 2
    assert graph.edge_count == 1

    edge = graph.edges[0]

    assert edge.relationship == "charged_fee"


def test_unmatched_reference_does_not_create_edge():

    invalid_refund = refund()
    invalid_refund["payment_ref"] = "PAY_UNKNOWN"

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            refunds=[invalid_refund],
        )
    )

    graph = RelationshipResolver().resolve(result)

    assert graph.node_count == 2
    assert graph.edge_count == 0