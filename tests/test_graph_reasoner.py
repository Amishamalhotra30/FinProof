from app.evidence.relationship_resolver import (
    RelationshipResolver,
)
from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)
from app.reconciliation.graph_reasoner import (
    GraphFindingType,
    GraphReasoner,
)
from app.reconciliation.models import (
    Cardinality,
    MatchMethod,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)
from app.reconciliation.resolver import (
    ReconciliationResolver,
)


def payment():

    return {
        "payment_id": "PAY_001",
        "order_ref": "ORDER_001",
        "amount": "50000.00",
        "captured_on": (
            "2026-08-31T10:00:00"
        ),
        "payment_status": "CAPTURED",
        "currency_code": "INR",
    }


def settlement():

    return {
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


def bank():

    return {
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


def build_graph(
    *,
    include_settlement=True,
    include_bank=True,
):

    source = MultiSourceInput(
        payments=[payment()],
        settlements=(
            [settlement()]
            if include_settlement
            else []
        ),
        bank=(
            [bank()]
            if include_bank
            else []
        ),
    )

    ingestion_result = ingest_sources(
        source
    )

    evidence_graph = (
        RelationshipResolver().resolve(
            ingestion_result
        )
    )

    return ReconciliationResolver().resolve(
        evidence_graph
    )


def test_complete_chain_has_no_findings():

    graph = build_graph()

    findings = GraphReasoner().reason(
        graph
    )

    assert findings == []


def test_missing_settlement_is_detected():

    graph = build_graph(
        include_settlement=False,
        include_bank=False,
    )

    findings = GraphReasoner().reason(
        graph
    )

    types = {
        finding.finding_type
        for finding in findings
    }

    assert (
        GraphFindingType.MISSING_SETTLEMENT
        in types
    )


def test_missing_bank_credit_is_detected():

    graph = build_graph(
        include_settlement=True,
        include_bank=False,
    )

    findings = GraphReasoner().reason(
        graph
    )

    types = {
        finding.finding_type
        for finding in findings
    }

    assert (
        GraphFindingType.MISSING_BANK_CREDIT
        in types
    )


def test_multiple_settlements_are_detected():

    graph = build_graph()

    graph.add_relationship(
        Relationship(
            relationship_id="REL_PAY_001_SET_002",
            source_record_id="PAY_001",
            target_record_id="SET_002",
            relationship_type=(
                RelationshipType
                .SETTLEMENT_FOR_PAYMENT
            ),
            cardinality=(
                Cardinality.ONE_TO_ONE
            ),
            method=(
                MatchMethod.AMOUNT_TIME_MATCH
            ),
            evidence=[
                "Competing settlement"
            ],
            status=(
                RelationshipStatus.CONFIRMED
            ),
            created_at=(
                __import__(
                    "datetime"
                ).datetime.now()
            ),
        )
    )

    findings = GraphReasoner().reason(
        graph
    )

    types = {
        finding.finding_type
        for finding in findings
    }

    assert (
        GraphFindingType.MULTIPLE_SETTLEMENTS
        in types
    )


def test_findings_are_explainable():

    graph = build_graph(
        include_settlement=True,
        include_bank=False,
    )

    findings = GraphReasoner().reason(
        graph
    )

    assert findings

    for finding in findings:

        assert finding.case_id
        assert finding.finding_type
        assert finding.severity
        assert finding.message
        assert isinstance(
            finding.evidence,
            list,
        )


def test_reasoner_does_not_modify_graph():

    graph = build_graph()

    before = (
        graph.relationship_count
    )

    GraphReasoner().reason(
        graph
    )

    assert (
        graph.relationship_count
        == before
    )