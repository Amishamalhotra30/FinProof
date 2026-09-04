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
from app.reconciliation.normalized_matcher import (
    NormalizedMatcher,
)


def payment(payment_id="PAY_001"):
    return {
        "payment_id": payment_id,
        "order_ref": "ORDER_001",
        "amount": "50000.00",
        "captured_on": "2026-08-31T10:00:00",
        "payment_status": "CAPTURED",
        "currency_code": "INR",
    }


def refund(payment_ref="PAY_001"):
    return {
        "refund_id": "REFUND_001",
        "payment_ref": payment_ref,
        "refund_amount": "1000.00",
        "created_on": "2026-08-31T11:00:00",
        "refund_status": "PROCESSED",
    }


def test_normalizes_identifier():

    assert (
        NormalizedMatcher.normalize(
            " pay-001 "
        )
        == "PAY001"
    )

    assert (
        NormalizedMatcher.normalize(
            "PAY_001"
        )
        == "PAY001"
    )


def test_normalized_match_links_payment_to_refund():

    result = ingest_sources(
        MultiSourceInput(
            payments=[
                payment("PAY_001")
            ],
            refunds=[
                refund(" pay-001 ")
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    graph = NormalizedMatcher().match(
        evidence_graph
    )

    assert graph.relationship_count == 1

    relationship = graph.relationships[0]

    assert (
        relationship.relationship_type
        == RelationshipType.REFUND_FOR_PAYMENT
    )

    assert (
        relationship.method
        == MatchMethod.NORMALIZED_ID
    )

    assert (
        relationship.status
        == RelationshipStatus.CONFIRMED
    )


def test_normalized_match_does_not_duplicate_exact_match():

    result = ingest_sources(
        MultiSourceInput(
            payments=[
                payment("PAY_001")
            ],
            refunds=[
                refund("PAY_001")
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    exact_graph = ExactMatcher().match(
        evidence_graph
    )

    normalized_graph = NormalizedMatcher().match(
        evidence_graph,
        existing_graph=exact_graph,
    )

    assert (
        normalized_graph.relationship_count
        == 1
    )

    assert (
        normalized_graph.relationships[0].method
        == MatchMethod.EXACT_ID
    )


def test_normalized_match_skips_ambiguous_candidates():

    result = ingest_sources(
        MultiSourceInput(
            payments=[
                payment("PAY_001"),
                payment("PAY-001"),
            ],
            refunds=[
                refund("PAY_001")
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    graph = NormalizedMatcher().match(
        evidence_graph
    )

    assert (
        graph.relationship_count
        == 0
    )


def test_normalized_match_does_not_guess_unknown_reference():

    result = ingest_sources(
        MultiSourceInput(
            payments=[
                payment("PAY_001")
            ],
            refunds=[
                refund("PAY_UNKNOWN")
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    graph = NormalizedMatcher().match(
        evidence_graph
    )

    assert (
        graph.relationship_count
        == 0
    )