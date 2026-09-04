from datetime import datetime
from decimal import Decimal

from app.domain.enums import EventType, RecordSource
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.investigation.evidence_retriever import (
    EvidenceRetriever,
    retrieve_evidence,
)
from app.investigation.models import (
    HypothesisType,
    InvestigationCase,
    InvestigationHypothesis,
)


def make_case(
    affected_event_ids=None,
) -> InvestigationCase:
    return InvestigationCase(
        case_id="CASE_0001",
        discrepancy_id="DISC_001",
        control_failure="SETTLEMENT_AMOUNT",
        affected_event_ids=(
            affected_event_ids
            if affected_event_ids is not None
            else ["PAYMENT_1"]
        ),
        expected_value=Decimal("50000.00"),
        observed_value=Decimal("47000.00"),
        difference=Decimal("-3000.00"),
        expected_state={
            "gross_captured": Decimal("50000.00"),
            "expected_settlement": Decimal("50000.00"),
        },
        observed_state={
            "gross_captured": Decimal("50000.00"),
            "total_settled": Decimal("47000.00"),
        },
    )


def make_graph() -> EventGraph:
    graph = EventGraph()

    payment = FinancialEvent(
        event_id="PAYMENT_1",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id="PAYMENT_1",
        amount=Decimal("50000.00"),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            30,
            9,
            0,
        ),
        related_event_ids=[
            "REFUND_1",
            "SETTLEMENT_1",
        ],
        source=RecordSource.PAYMENT,
        metadata={},
    )

    refund = FinancialEvent(
        event_id="REFUND_1",
        event_type=EventType.REFUND_CREATED,
        entity_id="REFUND_1",
        amount=Decimal("3000.00"),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            30,
            9,
            4,
        ),
        related_event_ids=[
            "PAYMENT_1",
        ],
        source=RecordSource.REFUND,
        metadata={},
    )

    settlement = FinancialEvent(
        event_id="SETTLEMENT_1",
        event_type=EventType.SETTLEMENT_PROCESSED,
        entity_id="PAYMENT_1",
        amount=Decimal("47000.00"),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            30,
            9,
            5,
        ),
        related_event_ids=[
            "PAYMENT_1",
        ],
        source=RecordSource.SETTLEMENT,
        metadata={},
    )

    unrelated = FinancialEvent(
        event_id="UNRELATED_1",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id="OTHER_PAYMENT",
        amount=Decimal("1000.00"),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            30,
            10,
            0,
        ),
        related_event_ids=[],
        source=RecordSource.PAYMENT,
        metadata={},
    )

    graph.add_event(payment)
    graph.add_event(refund)
    graph.add_event(settlement)
    graph.add_event(unrelated)

    return graph


def make_hypothesis(
    hypothesis_type: HypothesisType,
) -> InvestigationHypothesis:
    return InvestigationHypothesis(
        hypothesis_id="H001",
        hypothesis_type=hypothesis_type,
    )


def test_retriever_returns_affected_event():
    case = make_case()

    evidence = EvidenceRetriever().retrieve(
        case,
        make_graph(),
    )

    ids = {
        item.evidence_id
        for item in evidence
    }

    assert "PAYMENT_1" in ids


def test_retriever_returns_directly_related_events():
    case = make_case()

    evidence = retrieve_evidence(
        case,
        make_graph(),
    )

    ids = {
        item.evidence_id
        for item in evidence
    }

    assert ids == {
        "PAYMENT_1",
        "REFUND_1",
        "SETTLEMENT_1",
    }


def test_retriever_does_not_include_unrelated_events():
    case = make_case()

    evidence = retrieve_evidence(
        case,
        make_graph(),
    )

    ids = {
        item.evidence_id
        for item in evidence
    }

    assert "UNRELATED_1" not in ids


def test_retrieval_is_deterministic():
    case = make_case()

    retriever = EvidenceRetriever()

    first = retriever.retrieve(
        case,
        make_graph(),
    )

    second = retriever.retrieve(
        case,
        make_graph(),
    )

    assert first == second


def test_retrieval_deduplicates_evidence():
    case = make_case(
        affected_event_ids=[
            "PAYMENT_1",
            "REFUND_1",
        ]
    )

    evidence = retrieve_evidence(
        case,
        make_graph(),
    )

    ids = [
        item.evidence_id
        for item in evidence
    ]

    assert len(ids) == len(set(ids))


def test_refund_hypothesis_retrieves_refund_events():
    case = make_case()

    hypothesis = make_hypothesis(
        HypothesisType.REFUND
    )

    evidence = EvidenceRetriever().retrieve_for_hypothesis(
        case,
        hypothesis,
        make_graph(),
    )

    assert [
        item.evidence_id
        for item in evidence
    ] == ["REFUND_1"]


def test_fee_hypothesis_does_not_retrieve_refund():
    case = make_case()

    hypothesis = make_hypothesis(
        HypothesisType.FEE
    )

    evidence = EvidenceRetriever().retrieve_for_hypothesis(
        case,
        hypothesis,
        make_graph(),
    )

    assert evidence == []


def test_partial_settlement_retrieves_settlement_evidence():
    case = make_case()

    hypothesis = make_hypothesis(
        HypothesisType.PARTIAL_SETTLEMENT
    )

    evidence = EvidenceRetriever().retrieve_for_hypothesis(
        case,
        hypothesis,
        make_graph(),
    )

    assert {
        item.evidence_id
        for item in evidence
    } == {
        "SETTLEMENT_1",
    }


def test_broad_hypothesis_retrieves_candidate_events():
    case = make_case()

    hypothesis = make_hypothesis(
        HypothesisType.SOURCE_DATA_ERROR
    )

    evidence = EvidenceRetriever().retrieve_for_hypothesis(
        case,
        hypothesis,
        make_graph(),
    )

    assert {
        item.evidence_id
        for item in evidence
    } == {
        "PAYMENT_1",
        "REFUND_1",
        "SETTLEMENT_1",
    }


def test_retrieved_evidence_is_not_declared_supporting():
    case = make_case()

    hypothesis = make_hypothesis(
        HypothesisType.REFUND
    )

    evidence = EvidenceRetriever().retrieve_for_hypothesis(
        case,
        hypothesis,
        make_graph(),
    )

    assert len(evidence) == 1

    assert (
        evidence[0].relationship.value
        == "IRRELEVANT"
    )


def test_retriever_does_not_modify_graph():
    graph = make_graph()
    case = make_case()

    before = dict(graph.events)

    EvidenceRetriever().retrieve(
        case,
        graph,
    )

    assert graph.events == before