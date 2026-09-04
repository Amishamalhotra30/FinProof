from copy import deepcopy
from decimal import Decimal
from unittest.mock import Mock

from app.domain.events import FinancialEvent
from app.domain.enums import EventType, RecordSource
from app.domain.graph import EventGraph

from app.investigation.hypotheses import (
    HypothesisGenerator,
)
from app.investigation.hypothesis_evaluator import (
    HypothesisEvaluator,
)
from app.investigation.investigator import (
    InvestigationOrchestrator,
)
from app.investigation.models import (
    EvidenceRelation,
    HypothesisStatus,
    HypothesisType,
    InvestigationCase,
    InvestigationEvidence,
    InvestigationStatus,
)


# ============================================================
# Fixtures / helpers
# ============================================================


def make_case(
    *,
    difference: str = "5000.00",
    control_failure: str = "SETTLEMENT_AMOUNT",
) -> InvestigationCase:
    return InvestigationCase(
        case_id="CASE_0001",
        discrepancy_id="DISC_SETTLEMENT_AMOUNT",
        control_failure=control_failure,
        affected_event_ids=[
            "PAYMENT_1",
            "SETTLEMENT_1",
        ],
        expected_value=Decimal("50000.00"),
        observed_value=(
            Decimal("50000.00")
            - Decimal(difference)
        ),
        difference=Decimal(difference),
        expected_state={
            "gross_captured": Decimal("50000.00"),
            "expected_settlement": Decimal(
                "50000.00"
            ),
        },
        observed_state={
            "gross_captured": Decimal("50000.00"),
            "total_settled": (
                Decimal("50000.00")
                - Decimal(difference)
            ),
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
        timestamp="2026-08-30T10:00:00",
        related_event_ids=[
            "SETTLEMENT_1",
        ],
        source=RecordSource.PAYMENT,
        metadata={},
    )

    settlement = FinancialEvent(
        event_id="SETTLEMENT_1",
        event_type=EventType.SETTLEMENT_PROCESSED,
        entity_id="PAYMENT_1",
        amount=Decimal("45000.00"),
        currency="INR",
        timestamp="2026-08-30T10:05:00",
        related_event_ids=[
            "PAYMENT_1",
        ],
        source=RecordSource.SETTLEMENT,
        metadata={},
    )

    graph.add_event(payment)
    graph.add_event(settlement)

    return graph


def make_supporting_evidence(
    *,
    evidence_id: str = "EVIDENCE_1",
    amount: str = "5000.00",
) -> InvestigationEvidence:
    return InvestigationEvidence(
        evidence_id=evidence_id,
        source="settlement",
        record_id="SETTLEMENT_1",
        amount=Decimal(amount),
        timestamp="2026-08-30T10:05:00",
        relationship=EvidenceRelation.SUPPORTS,
        description="Settlement evidence explains the discrepancy.",
    )


def make_contradicting_evidence(
    *,
    evidence_id: str = "CONTRADICTION_1",
) -> InvestigationEvidence:
    return InvestigationEvidence(
        evidence_id=evidence_id,
        source="settlement",
        record_id="SETTLEMENT_1",
        amount=Decimal("5000.00"),
        timestamp="2026-08-30T10:05:00",
        relationship=EvidenceRelation.CONTRADICTS,
        description="Evidence contradicts this hypothesis.",
    )


# ============================================================
# Basic orchestration
# ============================================================


def test_investigator_returns_investigation_result():
    case = make_case()

    retriever = Mock()

    retriever.retrieve_for_hypothesis.return_value = [
        make_supporting_evidence()
    ]

    orchestrator = InvestigationOrchestrator(
        hypothesis_generator=HypothesisGenerator(),
        evidence_retriever=retriever,
        hypothesis_evaluator=HypothesisEvaluator(),
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.case_id == case.case_id
    assert result.discrepancy_id == case.discrepancy_id
    assert result.investigation_id == (
        "INV_CASE_0001_DISC_SETTLEMENT_AMOUNT"
    )

    assert result.hypotheses


def test_investigator_calls_retriever_for_each_hypothesis():
    case = make_case()

    retriever = Mock()
    retriever.retrieve_for_hypothesis.return_value = []

    generator = HypothesisGenerator()

    expected_hypothesis_count = len(
        generator.generate(case)
    )

    orchestrator = InvestigationOrchestrator(
        hypothesis_generator=generator,
        evidence_retriever=retriever,
        hypothesis_evaluator=HypothesisEvaluator(),
    )

    orchestrator.investigate(
        case,
        make_graph(),
    )

    assert (
        retriever.retrieve_for_hypothesis.call_count
        == expected_hypothesis_count
    )


def test_investigator_calls_retriever_with_case_hypothesis_and_graph():
    case = make_case()

    graph = make_graph()

    retriever = Mock()
    retriever.retrieve_for_hypothesis.return_value = []

    generator = Mock()

    hypothesis = generator.generate.return_value = (
        [
            HypothesisGenerator().generate(case)[0]
        ]
    )

    orchestrator = InvestigationOrchestrator(
        hypothesis_generator=generator,
        evidence_retriever=retriever,
        hypothesis_evaluator=HypothesisEvaluator(),
    )

    orchestrator.investigate(
        case,
        graph,
    )

    retriever.retrieve_for_hypothesis.assert_called_once_with(
        case,
        hypothesis[0],
        graph,
    )


# ============================================================
# Resolution
# ============================================================


def test_fully_explained_discrepancy_is_resolved():
    case = make_case(
        difference="5000.00"
    )

    retriever = Mock()

    retriever.retrieve_for_hypothesis.return_value = [
        make_supporting_evidence(
            amount="5000.00"
        )
    ]

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.status == InvestigationStatus.RESOLVED
    assert result.explained_amount == Decimal(
        "5000.00"
    )
    assert result.remaining_unexplained == Decimal(
        "0"
    )


def test_partially_explained_discrepancy_is_unresolved():
    case = make_case(
        difference="5000.00"
    )

    retriever = Mock()

    retriever.retrieve_for_hypothesis.return_value = [
        make_supporting_evidence(
            amount="2000.00"
        )
    ]

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.status == InvestigationStatus.UNRESOLVED
    assert result.explained_amount == Decimal(
        "2000.00"
    )
    assert result.remaining_unexplained == Decimal(
        "3000.00"
    )


# ============================================================
# Insufficient evidence
# ============================================================


def test_no_decisive_evidence_is_insufficient():
    case = make_case()

    retriever = Mock()
    retriever.retrieve_for_hypothesis.return_value = []

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert (
        result.status
        == InvestigationStatus.INSUFFICIENT_EVIDENCE
    )

    assert result.explained_amount == Decimal(
        "0"
    )

    assert result.remaining_unexplained == Decimal(
        "5000.00"
    )


# ============================================================
# Contradiction
# ============================================================


def test_contradicting_evidence_produces_contradiction():
    case = make_case()

    retriever = Mock()
    retriever.retrieve_for_hypothesis.return_value = [
        make_contradicting_evidence()
    ]

    # Use a single hypothesis so the test specifically
    # exercises contradiction handling.
    generator = Mock()

    hypothesis = HypothesisGenerator().generate(
        case
    )[0]

    generator.generate.return_value = [
        hypothesis
    ]

    orchestrator = InvestigationOrchestrator(
        hypothesis_generator=generator,
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert (
        result.status
        == InvestigationStatus.CONTRADICTION
    )

    assert result.explained_amount == Decimal(
        "0"
    )


# ============================================================
# Evidence aggregation
# ============================================================


def test_supporting_evidence_ids_are_aggregated():
    case = make_case()

    retriever = Mock()

    retriever.retrieve_for_hypothesis.side_effect = [
        [
            make_supporting_evidence(
                evidence_id="EVIDENCE_A",
                amount="1000.00",
            )
        ],
        [
            make_supporting_evidence(
                evidence_id="EVIDENCE_B",
                amount="1000.00",
            )
        ],
        [],
        [],
        [],
        [],
        [],
    ]

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.supporting_evidence_ids == [
        "EVIDENCE_A",
        "EVIDENCE_B",
    ]


def test_duplicate_supporting_evidence_ids_are_removed():
    case = make_case()

    retriever = Mock()

    evidence = make_supporting_evidence(
        evidence_id="EVIDENCE_DUP",
        amount="1000.00",
    )

    retriever.retrieve_for_hypothesis.side_effect = [
        [evidence],
        [evidence],
        [],
        [],
        [],
        [],
        [],
    ]

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.supporting_evidence_ids == [
        "EVIDENCE_DUP"
    ]


# ============================================================
# Amount safety
# ============================================================


def test_explained_amount_is_capped_at_discrepancy():
    case = make_case(
        difference="5000.00"
    )

    retriever = Mock()

    retriever.retrieve_for_hypothesis.return_value = [
        make_supporting_evidence(
            amount="9000.00"
        )
    ]

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.explained_amount == Decimal(
        "5000.00"
    )

    assert result.remaining_unexplained == Decimal(
        "0"
    )


def test_remaining_unexplained_never_becomes_negative():
    case = make_case(
        difference="5000.00"
    )

    retriever = Mock()

    retriever.retrieve_for_hypothesis.return_value = [
        make_supporting_evidence(
            amount="10000.00"
        )
    ]

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.remaining_unexplained >= Decimal(
        "0"
    )


# ============================================================
# Validation boundary
# ============================================================


def test_investigation_result_is_not_marked_validated():
    case = make_case()

    retriever = Mock()
    retriever.retrieve_for_hypothesis.return_value = []

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    result = orchestrator.investigate(
        case,
        make_graph(),
    )

    assert result.validated is False


# ============================================================
# Case immutability
# ============================================================


def test_investigator_does_not_modify_case():
    case = make_case()

    before = deepcopy(
        case.model_dump()
    )

    retriever = Mock()
    retriever.retrieve_for_hypothesis.return_value = []

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    orchestrator.investigate(
        case,
        make_graph(),
    )

    after = case.model_dump()

    assert after == before


# ============================================================
# Deterministic ordering
# ============================================================


def test_hypothesis_order_is_deterministic():
    case = make_case()

    retriever = Mock()
    retriever.retrieve_for_hypothesis.return_value = []

    orchestrator = InvestigationOrchestrator(
        evidence_retriever=retriever,
    )

    first = orchestrator.investigate(
        case,
        make_graph(),
    )

    second = orchestrator.investigate(
        case,
        make_graph(),
    )

    first_types = [
        finding.hypothesis_type
        for finding in first.hypotheses
    ]

    second_types = [
        finding.hypothesis_type
        for finding in second.hypotheses
    ]

    assert first_types == second_types


# ============================================================
# Convenience API
# ============================================================


def test_investigate_convenience_function_exists():
    from app.investigation.investigator import (
        investigate,
    )

    case = make_case()

    result = investigate(
        case,
        make_graph(),
    )

    assert result.case_id == "CASE_0001"