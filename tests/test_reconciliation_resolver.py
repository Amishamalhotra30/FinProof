from app.evidence.relationship_resolver import (
    RelationshipResolver,
)
from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)
from app.reconciliation.models import (
    MatchMethod,
    RelationshipStatus,
    RelationshipType,
)
from app.reconciliation.resolver import (
    ReconciliationResolver,
)


def payment(
    payment_id="PAY_001",
):

    return {
        "payment_id": payment_id,
        "order_ref": "ORDER_001",
        "amount": "50000.00",
        "captured_on": (
            "2026-08-31T10:00:00"
        ),
        "payment_status": "CAPTURED",
        "currency_code": "INR",
    }


def refund(
    payment_ref="PAY_001",
):

    return {
        "refund_id": "REFUND_001",
        "payment_ref": payment_ref,
        "refund_amount": "1000.00",
        "created_on": (
            "2026-08-31T11:00:00"
        ),
        "refund_status": "PROCESSED",
    }


def settlement(
    settlement_id="SET_001",
    payment_ref="PAY_001",
    net="49500.00",
    utr="UTR001",
):

    return {
        "settlement_id": settlement_id,
        "payment_ref": payment_ref,
        "reference": payment_ref,
        "gross": "50000.00",
        "fees": "500.00",
        "tax": "0.00",
        "adjustment": "0.00",
        "net": net,
        "processed_at": (
            "2026-08-31T12:00:00"
        ),
        "status": "CREATED",
        "utr": utr,
    }


def bank(
    transaction_ref="BANK_001",
    credit="49500.00",
    utr="UTR001",
):

    return {
        "transaction_ref": transaction_ref,
        "narration": "Settlement credit",
        "credit": credit,
        "debit": "0.00",
        "value_date": (
            "2026-08-31T12:15:00"
        ),
        "currency": "INR",
        "utr": utr,
    }


def build_graph(inputs):

    result = ingest_sources(inputs)

    return RelationshipResolver().resolve(
        result
    )


def test_resolver_preserves_exact_relationships():

    evidence_graph = build_graph(
        MultiSourceInput(
            payments=[
                payment()
            ],
            refunds=[
                refund()
            ],
        )
    )

    graph = ReconciliationResolver().resolve(
        evidence_graph
    )

    assert graph.relationship_count == 1

    relationship = (
        graph.relationships[0]
    )

    assert (
        relationship.relationship_type
        == RelationshipType.REFUND_FOR_PAYMENT
    )

    assert (
        relationship.method
        == MatchMethod.EXACT_ID
    )

    assert (
        relationship.status
        == RelationshipStatus.CONFIRMED
    )


def test_resolver_builds_payment_settlement_chain():

    evidence_graph = build_graph(
        MultiSourceInput(
            payments=[
                payment()
            ],
            settlements=[
                settlement()
            ],
        )
    )

    graph = ReconciliationResolver().resolve(
        evidence_graph
    )

    assert graph.relationship_count == 1

    relationship = (
        graph.relationships[0]
    )

    assert (
        relationship.relationship_type
        == RelationshipType.SETTLEMENT_FOR_PAYMENT
    )


def test_resolver_builds_settlement_bank_chain():

    evidence_graph = build_graph(
        MultiSourceInput(
            payments=[
                payment()
            ],
            settlements=[
                settlement()
            ],
            bank=[
                bank()
            ],
        )
    )

    graph = ReconciliationResolver().resolve(
        evidence_graph
    )

    assert graph.relationship_count == 2

    types = {
        relationship.relationship_type
        for relationship
        in graph.relationships
    }

    assert (
        RelationshipType.SETTLEMENT_FOR_PAYMENT
        in types
    )

    assert (
        RelationshipType.BANK_FOR_SETTLEMENT
        in types
    )


def test_resolver_does_not_duplicate_exact_relationships():

    evidence_graph = build_graph(
        MultiSourceInput(
            payments=[
                payment()
            ],
            refunds=[
                refund()
            ],
        )
    )

    graph = ReconciliationResolver().resolve(
        evidence_graph
    )

    refund_relationships = [
        relationship
        for relationship
        in graph.relationships
        if (
            relationship.relationship_type
            == RelationshipType.REFUND_FOR_PAYMENT
        )
    ]

    assert len(
        refund_relationships
    ) == 1


def test_resolver_keeps_unresolved_candidates_out_of_graph():

    evidence_graph = build_graph(
        MultiSourceInput(
            payments=[
                payment()
            ],
            settlements=[
                settlement(
                    payment_ref="PAY_UNKNOWN"
                )
            ],
        )
    )

    graph = ReconciliationResolver().resolve(
        evidence_graph
    )

    assert graph.relationship_count == 0