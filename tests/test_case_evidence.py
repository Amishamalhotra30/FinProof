from app.evidence.case import (
    CaseEvidenceAssembler,
)
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


def test_builds_case_evidence():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            refunds=[refund()],
            fees=[fee()],
        )
    )

    graph = RelationshipResolver().resolve(
        result
    )

    case = CaseEvidenceAssembler().build(
        graph,
        "PAY_001",
    )

    assert case.case_id == "PAY_001"

    assert (
        case.root.record_type
        == "payment"
    )

    assert len(case.nodes) == 3
    assert len(case.edges) == 2


def test_case_evidence_contains_related_types():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            refunds=[refund()],
            fees=[fee()],
        )
    )

    graph = RelationshipResolver().resolve(
        result
    )

    case = CaseEvidenceAssembler().build(
        graph,
        "PAY_001",
    )

    assert len(
        case.nodes_by_type("payment")
    ) == 1

    assert len(
        case.nodes_by_type("refund")
    ) == 1

    assert len(
        case.nodes_by_type("fee")
    ) == 1


def test_case_evidence_includes_settlement_to_bank_chain():

    settlement = {
        "settlement_id": "SETTLEMENT_001",
        "payment_ref": "PAY_001",
        "reference": "PAY_001",
        "gross": "50000.00",
        "fees": "500.00",
        "tax": "0.00",
        "adjustment": "0.00",
        "net": "49500.00",
        "processed_at": "2026-08-31T12:00:00",
        "status": "CREATED",
        "utr": "UTR001",
    }

    bank = {
        "transaction_ref": "BANK_001",
        "narration": "Settlement credit",
        "credit": "49500.00",
        "debit": "0.00",
        "value_date": "2026-08-31T12:15:00",
        "currency": "INR",
        "utr": "UTR001",
    }

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
            settlements=[settlement],
            bank=[bank],
        )
    )

    graph = RelationshipResolver().resolve(
        result
    )

    case = CaseEvidenceAssembler().build(
        graph,
        "PAY_001",
    )

    assert len(
        case.nodes_by_type("payment")
    ) == 1

    assert len(
        case.nodes_by_type("settlement")
    ) == 1

    assert len(
        case.nodes_by_type("bank")
    ) == 1

    assert len(case.edges) == 2

    relationships = {
        edge.relationship
        for edge in case.edges
    }

    assert (
        "settled_by"
        in relationships
    )

    assert (
        "credited_to"
        in relationships
    )


def test_missing_payment_is_rejected():

    result = ingest_sources(
        MultiSourceInput(
            payments=[payment()],
        )
    )

    graph = RelationshipResolver().resolve(
        result
    )

    try:
        CaseEvidenceAssembler().build(
            graph,
            "PAY_UNKNOWN",
        )

        assert False

    except ValueError as exc:

        assert (
            str(exc)
            == "Payment not found: PAY_UNKNOWN"
        )