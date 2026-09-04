from app.evidence.relationship_resolver import (
    RelationshipResolver,
)
from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)
from app.reconciliation.exact_matcher import (
    ExactMatcher,
)
from app.reconciliation.models import (
    MatchMethod,
    RelationshipStatus,
    RelationshipType,
)


def test_exact_matcher_links_payment_to_refund():

    result = ingest_sources(
        MultiSourceInput(
            payments=[
                {
                    "payment_id": "PAY_001",
                    "order_ref": "ORDER_001",
                    "amount": "50000.00",
                    "captured_on": (
                        "2026-08-31T10:00:00"
                    ),
                    "payment_status": "CAPTURED",
                    "currency_code": "INR",
                }
            ],
            refunds=[
                {
                    "refund_id": "REFUND_001",
                    "payment_ref": "PAY_001",
                    "refund_amount": "1000.00",
                    "created_on": (
                        "2026-08-31T11:00:00"
                    ),
                    "refund_status": "PROCESSED",
                }
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    graph = ExactMatcher().match(
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


def test_exact_matcher_links_settlement_to_bank():

    result = ingest_sources(
        MultiSourceInput(
            payments=[
                {
                    "payment_id": "PAY_001",
                    "order_ref": "ORDER_001",
                    "amount": "50000.00",
                    "captured_on": (
                        "2026-08-31T10:00:00"
                    ),
                    "payment_status": "CAPTURED",
                    "currency_code": "INR",
                }
            ],
            settlements=[
                {
                    "settlement_id": "SET_001",
                    "payment_ref": "PAY_001",
                    "reference": "PAY_001",
                    "gross": "50000.00",
                    "fees": "500.00",
                    "tax": "0.00",
                    "adjustment": "0.00",
                    "net": "49500.00",
                    "processed_at": (
                        "2026-08-31T12:00:00"
                    ),
                    "status": "CREATED",
                    "utr": "UTR001",
                }
            ],
            bank=[
                {
                    "transaction_ref": "BANK_001",
                    "narration": "Settlement credit",
                    "credit": "49500.00",
                    "debit": "0.00",
                    "value_date": (
                        "2026-08-31T12:15:00"
                    ),
                    "currency": "INR",
                    "utr": "UTR001",
                }
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    graph = ExactMatcher().match(
        evidence_graph
    )

    relationships = graph.relationships

    assert len(relationships) == 2

    types = {
        relationship.relationship_type
        for relationship in relationships
    }

    assert (
        RelationshipType.SETTLEMENT_FOR_PAYMENT
        in types
    )

    assert (
        RelationshipType.BANK_FOR_SETTLEMENT
        in types
    )


def test_exact_matcher_does_not_guess_missing_reference():

    result = ingest_sources(
        MultiSourceInput(
            payments=[
                {
                    "payment_id": "PAY_001",
                    "order_ref": "ORDER_001",
                    "amount": "50000.00",
                    "captured_on": (
                        "2026-08-31T10:00:00"
                    ),
                    "payment_status": "CAPTURED",
                    "currency_code": "INR",
                }
            ],
            refunds=[
                {
                    "refund_id": "REFUND_001",
                    "payment_ref": "PAY_UNKNOWN",
                    "refund_amount": "1000.00",
                    "created_on": (
                        "2026-08-31T11:00:00"
                    ),
                    "refund_status": "PROCESSED",
                }
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    graph = ExactMatcher().match(
        evidence_graph
    )

    assert graph.relationship_count == 0