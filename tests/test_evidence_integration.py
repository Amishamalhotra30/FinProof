from app.evidence.case import CaseEvidenceAssembler
from app.evidence.relationship_resolver import (
    RelationshipResolver,
)
from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)


def test_end_to_end_evidence_pipeline():

    payment = {
        "payment_id": "PAY_001",
        "order_ref": "ORDER_001",
        "amount": "50000.00",
        "captured_on": "2026-08-31T10:00:00",
        "payment_status": "CAPTURED",
        "currency_code": "INR",
    }

    refund = {
        "refund_id": "REFUND_001",
        "payment_ref": "PAY_001",
        "refund_amount": "1000.00",
        "created_on": "2026-08-31T11:00:00",
        "refund_status": "PROCESSED",
    }

    fee = {
        "fee_id": "FEE_001",
        "payment_ref": "PAY_001",
        "fee_amount": "500.00",
        "created_on": "2026-08-31T11:30:00",
        "fee_status": "APPLIED",
    }

    settlement = {
        "settlement_id": "SETTLEMENT_001",
        "payment_ref": "PAY_001",
        "reference": "PAY_001",
        "gross": "50000.00",
        "fees": "500.00",
        "tax": "0.00",
        "adjustment": "0.00",
        "net": "48500.00",
        "processed_at": "2026-08-31T12:00:00",
        "status": "CREATED",
        "utr": "UTR001",
    }

    bank = {
        "transaction_ref": "BANK_001",
        "narration": "Settlement credit",
        "credit": "48500.00",
        "debit": "0.00",
        "value_date": "2026-08-31T12:15:00",
        "currency": "INR",
        "utr": "UTR001",
    }

    # ---------------------------------------------------------
    # 1. INGEST
    # ---------------------------------------------------------

    ingestion_result = ingest_sources(
        MultiSourceInput(
            payments=[payment],
            refunds=[refund],
            fees=[fee],
            settlements=[settlement],
            bank=[bank],
        )
    )

    assert len(
        ingestion_result.payments.valid_records
    ) == 1

    assert len(
        ingestion_result.refunds.valid_records
    ) == 1

    assert len(
        ingestion_result.fees.valid_records
    ) == 1

    assert len(
        ingestion_result.settlements.valid_records
    ) == 1

    assert len(
        ingestion_result.bank.valid_records
    ) == 1

    # ---------------------------------------------------------
    # 2. BUILD GRAPH
    # ---------------------------------------------------------

    graph = RelationshipResolver().resolve(
        ingestion_result
    )

    assert graph.node_count == 5
    assert graph.edge_count == 4

    # ---------------------------------------------------------
    # 3. ASSEMBLE CASE
    # ---------------------------------------------------------

    case = CaseEvidenceAssembler().build(
        graph,
        "PAY_001",
    )

    assert case.case_id == "PAY_001"

    assert (
        case.root.record_type
        == "payment"
    )

    assert len(case.nodes) == 5
    assert len(case.edges) == 4

    # ---------------------------------------------------------
    # 4. VERIFY COMPLETE EVIDENCE CHAIN
    # ---------------------------------------------------------

    record_types = {
        node.record_type
        for node in case.nodes
    }

    assert record_types == {
        "payment",
        "refund",
        "fee",
        "settlement",
        "bank",
    }

    relationships = {
        edge.relationship
        for edge in case.edges
    }

    assert relationships == {
        "refunded_by",
        "charged_fee",
        "settled_by",
        "credited_to",
    }