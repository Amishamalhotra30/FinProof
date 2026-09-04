from decimal import Decimal

from app.evidence.graph import EvidenceGraph
from app.reconciliation.ai_inference import (
    AIInferenceEngine,
    DeterministicAIInferenceProvider,
)
from app.reconciliation.service import (
    ReconciliationService,
)


class Record:

    def __init__(self, evidence_id):
        self.evidence_id = evidence_id


def make_empty_graph():

    return EvidenceGraph()


def test_service_returns_reconciliation_result():

    result = ReconciliationService().reconcile(
        make_empty_graph()
    )

    assert result is not None
    assert result.graph is not None
    assert result.metrics is not None


def test_empty_graph_produces_empty_result():

    result = ReconciliationService().reconcile(
        make_empty_graph()
    )

    assert result.node_count == 0
    assert result.relationship_count == 0
    assert result.review_items == ()


def test_empty_graph_metrics_are_zero():

    result = (
        ReconciliationService()
        .reconcile_with_fixed_time(
            make_empty_graph(),
            Decimal("100"),
        )
    )

    assert (
        result.metrics.relationships_processed
        == 0
    )

    assert (
        result.metrics.confirmed_relationships
        == 0
    )

    assert (
        result.metrics.ambiguous_relationships
        == 0
    )

    assert (
        result.metrics.unresolved_relationships
        == 0
    )


def test_service_does_not_invoke_ai_without_ai_cases():

    provider = (
        DeterministicAIInferenceProvider()
    )

    engine = AIInferenceEngine(
        provider
    )

    result = ReconciliationService(
        ai_engine=engine,
    ).reconcile(
        make_empty_graph()
    )

    assert result.review_items == ()


def test_service_can_process_explicit_ai_case():

    provider = (
        DeterministicAIInferenceProvider()
    )

    engine = AIInferenceEngine(
        provider
    )

    source = Record("BANK_001")
    candidate = Record("SET_001")

    result = ReconciliationService(
        ai_engine=engine,
    ).reconcile(
        make_empty_graph(),
        ai_cases=[
            (
                source,
                [candidate],
            )
        ],
    )

    assert len(
        result.review_items
    ) == 1

    review = result.review_items[0]

    assert review.source_record_id == (
        "BANK_001"
    )

    assert review.candidate_record_id == (
        "SET_001"
    )

    assert review.requires_review is True


def test_ai_case_does_not_create_relationship():

    provider = (
        DeterministicAIInferenceProvider()
    )

    engine = AIInferenceEngine(
        provider
    )

    source = Record("BANK_001")
    candidate = Record("SET_001")

    result = ReconciliationService(
        ai_engine=engine,
    ).reconcile(
        make_empty_graph(),
        ai_cases=[
            (
                source,
                [candidate],
            )
        ],
    )

    assert result.relationship_count == 0
    assert len(result.review_items) == 1


def test_service_metrics_use_reconciliation_graph():

    result = (
        ReconciliationService()
        .reconcile_with_fixed_time(
            make_empty_graph(),
            Decimal("500"),
        )
    )

    assert (
        result.metrics.processing_time_ms
        == Decimal("500")
    )


def test_fixed_time_variant_is_reproducible():

    first = (
        ReconciliationService()
        .reconcile_with_fixed_time(
            make_empty_graph(),
            Decimal("100"),
        )
    )

    second = (
        ReconciliationService()
        .reconcile_with_fixed_time(
            make_empty_graph(),
            Decimal("100"),
        )
    )

    assert (
        first.metrics.processing_time_ms
        == second.metrics.processing_time_ms
    )


def test_review_items_are_exposed_separately():

    provider = (
        DeterministicAIInferenceProvider()
    )

    engine = AIInferenceEngine(
        provider
    )

    result = ReconciliationService(
        ai_engine=engine,
    ).reconcile(
        make_empty_graph(),
        ai_cases=[
            (
                Record("BANK_001"),
                [
                    Record("SET_001"),
                    Record("SET_002"),
                ],
            )
        ],
    )

    assert len(result.review_items) == 2
    assert len(
        result.ambiguous_review_items
    ) == 2


def test_non_ai_service_has_no_review_items():

    result = ReconciliationService().reconcile(
        make_empty_graph()
    )

    assert result.review_items == ()
    assert result.ambiguous_review_items == ()


def test_service_preserves_empty_input_graph():

    graph = make_empty_graph()

    before_nodes = dict(graph.nodes)

    ReconciliationService().reconcile(
        graph
    )

    assert graph.nodes == before_nodes

def test_ai_is_only_used_for_explicit_cases():

    class CountingProvider(
        DeterministicAIInferenceProvider
    ):

        def __init__(self):
            self.calls = 0

        def infer(
            self,
            source_record,
            candidates,
        ):
            self.calls += 1

            return super().infer(
                source_record,
                candidates,
            )

    provider = CountingProvider()

    engine = AIInferenceEngine(
        provider
    )

    service = ReconciliationService(
        ai_engine=engine
    )

    service.reconcile(
        make_empty_graph()
    )

    assert provider.calls == 0

    service.reconcile(
        make_empty_graph(),
        ai_cases=[
            (
                Record("BANK_001"),
                [Record("SET_001")],
            )
        ],
    )

    assert provider.calls == 1