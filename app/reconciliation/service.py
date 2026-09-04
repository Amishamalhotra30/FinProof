from dataclasses import dataclass
from decimal import Decimal

from app.evidence.graph import EvidenceGraph
from app.reconciliation.ai_inference import (
    AIInferenceEngine,
)
from app.reconciliation.metrics import (
    ReconciliationMetrics,
    ReconciliationMetricsCalculator,
    ReconciliationTimer,
)
from app.reconciliation.review import (
    ReviewEscalator,
    ReviewItem,
)
from app.reconciliation.resolver import (
    ReconciliationResolver,
)
from app.reconciliation.graph import (
    ReconciliationGraph,
)


@dataclass(frozen=True)
class ReconciliationServiceResult:
    """
    Complete Phase 3 reconciliation output.

    Contains the relationship graph, AI review items, and
    reconciliation metrics.

    This object does not contain financial correctness judgments.
    """

    graph: ReconciliationGraph

    review_items: tuple[ReviewItem, ...]

    metrics: ReconciliationMetrics

    @property
    def relationships(self):
        return tuple(self.graph.relationships)

    @property
    def ambiguous_review_items(self):
        return tuple(
            item
            for item in self.review_items
            if item.requires_review
        )

    @property
    def relationship_count(self) -> int:
        return self.graph.relationship_count

    @property
    def node_count(self) -> int:
        return self.graph.node_count


class ReconciliationService:
    """
    Public orchestration boundary for Phase 3.

    Responsibilities:

        1. Run deterministic reconciliation.
        2. Optionally invoke AI for explicitly supplied
           ambiguous candidate groups.
        3. Escalate AI proposals to review items.
        4. Calculate reconciliation metrics.

    It does not:

        - determine financial correctness
        - reconstruct financial events
        - access ground truth
        - repair canonical evidence
        - fabricate records
    """

    def __init__(
        self,
        resolver: ReconciliationResolver | None = None,
        ai_engine: AIInferenceEngine | None = None,
        review_escalator: ReviewEscalator | None = None,
    ):
        self.resolver = (
            resolver
            or ReconciliationResolver()
        )

        self.ai_engine = ai_engine

        self.review_escalator = (
            review_escalator
            or ReviewEscalator()
        )

    def reconcile(
        self,
        evidence_graph: EvidenceGraph,
        *,
        ai_cases=None,
    ) -> ReconciliationServiceResult:
        """
        Reconcile an evidence graph.

        `ai_cases` is optional and represents explicitly selected
        residual ambiguity cases.

        Expected structure:

            [
                (source_record, [candidate_record, ...]),
                ...
            ]

        AI is never invoked unless these cases are explicitly
        supplied.
        """

        timer = ReconciliationTimer()

        timer.start()

        graph = self.resolver.resolve(
            evidence_graph
        )

        review_items: list[ReviewItem] = []

        if (
            ai_cases
            and self.ai_engine is not None
        ):
            review_items = (
                self._process_ai_cases(
                    ai_cases
                )
            )

        elapsed_ms = timer.elapsed_ms()

        metrics = (
            ReconciliationMetricsCalculator
            .calculate(
                graph.relationships,
                elapsed_ms,
            )
        )

        return ReconciliationServiceResult(
            graph=graph,
            review_items=tuple(
                review_items
            ),
            metrics=metrics,
        )

    def reconcile_with_fixed_time(
        self,
        evidence_graph: EvidenceGraph,
        processing_time_ms: Decimal | str | int | float,
        *,
        ai_cases=None,
    ) -> ReconciliationServiceResult:
        """
        Deterministic/testing variant where processing time is
        explicitly supplied.

        Useful for reproducible metric tests.
        """

        graph = self.resolver.resolve(
            evidence_graph
        )

        review_items: list[ReviewItem] = []

        if (
            ai_cases
            and self.ai_engine is not None
        ):
            review_items = (
                self._process_ai_cases(
                    ai_cases
                )
            )

        metrics = (
            ReconciliationMetricsCalculator
            .calculate(
                graph.relationships,
                processing_time_ms,
            )
        )

        return ReconciliationServiceResult(
            graph=graph,
            review_items=tuple(
                review_items
            ),
            metrics=metrics,
        )

    def _process_ai_cases(
        self,
        ai_cases,
    ) -> list[ReviewItem]:

        review_items: list[ReviewItem] = []

        for source_record, candidates in ai_cases:

            proposals = self.ai_engine.infer(
                source_record,
                candidates,
            )

            review_items.extend(
                self.review_escalator.escalate_many(
                    proposals
                )
            )

        return review_items