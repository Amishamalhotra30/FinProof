from app.evidence.relationship_resolver import (
    RelationshipResolver,
)
from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)
from app.reconciliation.candidate_generator import (
    CandidateGenerator,
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


def settlement(
    settlement_id,
    payment_ref,
    net,
    utr=None,
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
        "processed_at": "2026-08-31T12:00:00",
        "status": "CREATED",
        "utr": utr,
    }


def bank(
    transaction_ref,
    credit,
    utr=None,
):

    return {
        "transaction_ref": transaction_ref,
        "narration": "Settlement credit",
        "credit": credit,
        "debit": "0.00",
        "value_date": "2026-08-31T12:15:00",
        "currency": "INR",
        "utr": utr,
    }


def test_generates_payment_settlement_candidates():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            settlements=[
                settlement(
                    "SET_001",
                    "PAY_001",
                    "49500.00",
                ),
                settlement(
                    "SET_002",
                    "PAY_002",
                    "49500.00",
                ),
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    candidates = CandidateGenerator().generate(
        evidence_graph
    )

    payment_settlement_candidates = [
        candidate
        for candidate in candidates
        if candidate.relationship_type
        == "SETTLEMENT_FOR_PAYMENT"
    ]

    assert len(
        payment_settlement_candidates
    ) == 2


def test_candidate_contains_amount_and_time_features():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            settlements=[
                settlement(
                    "SET_001",
                    "PAY_001",
                    "49500.00",
                )
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    candidates = CandidateGenerator().generate(
        evidence_graph
    )

    candidate = candidates[0]

    assert (
        candidate.features.amount_difference
        == 500
    )

    assert (
        candidate.features.time_difference_seconds
        == 7200
    )


def test_candidate_detects_exact_reference_feature():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            settlements=[
                settlement(
                    "SET_001",
                    "PAY_001",
                    "49500.00",
                )
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    candidates = CandidateGenerator().generate(
        evidence_graph
    )

    candidate = candidates[0]

    assert (
        candidate.features.reference_match
        is True
    )


def test_generates_settlement_bank_candidates():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            settlements=[
                settlement(
                    "SET_001",
                    "PAY_001",
                    "49500.00",
                    "UTR001",
                )
            ],
            bank=[
                bank(
                    "BANK_001",
                    "49500.00",
                    "UTR001",
                )
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    candidates = CandidateGenerator().generate(
        evidence_graph
    )

    bank_candidates = [
        candidate
        for candidate in candidates
        if candidate.relationship_type
        == "BANK_FOR_SETTLEMENT"
    ]

    assert len(bank_candidates) == 1

    assert (
        bank_candidates[0]
        .features.utr_match
        is True
    )


def test_candidate_generation_does_not_confirm_relationships():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            settlements=[
                settlement(
                    "SET_001",
                    "PAY_001",
                    "49500.00",
                )
            ],
        )
    )

    evidence_graph = (
        RelationshipResolver().resolve(result)
    )

    candidates = CandidateGenerator().generate(
        evidence_graph
    )

    assert len(candidates) == 1

    # A candidate is merely a possibility.
    # It must not itself become a confirmed
    # reconciliation relationship.
    assert not hasattr(
        candidates[0],
        "status",
    )