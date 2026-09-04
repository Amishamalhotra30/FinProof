from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from time import perf_counter

from app.reconciliation.models import (
    RelationshipStatus,
)


@dataclass(frozen=True)
class ReconciliationMetrics:
    """
    Explicit metrics describing reconciliation performance.

    Precision and recall are evaluation metrics and therefore
    require an externally supplied ground-truth relationship set.

    The normal reconciliation runtime does not access ground truth.
    """

    relationships_processed: int
    confirmed_relationships: int
    ambiguous_relationships: int
    unresolved_relationships: int
    ai_assisted_relationships: int

    processing_time_ms: Decimal

    relationship_precision: Decimal | None = None
    relationship_recall: Decimal | None = None

    @property
    def ambiguity_rate(self) -> Decimal:
        if self.relationships_processed == 0:
            return Decimal("0")

        return (
            Decimal(self.ambiguous_relationships)
            / Decimal(self.relationships_processed)
        )

    @property
    def ai_assisted_rate(self) -> Decimal:
        if self.relationships_processed == 0:
            return Decimal("0")

        return (
            Decimal(self.ai_assisted_relationships)
            / Decimal(self.relationships_processed)
        )

    @property
    def throughput(self) -> Decimal:
        """
        Confirmed relationships processed per second.
        """

        seconds = (
            self.processing_time_ms
            / Decimal("1000")
        )

        if seconds <= 0:
            return Decimal("0")

        return (
            Decimal(self.relationships_processed)
            / seconds
        )


class ReconciliationMetricsCalculator:
    """
    Calculates reconciliation metrics from relationship outputs.

    Ground truth is accepted only explicitly through the evaluation
    methods. It is never read from the reconciliation runtime.
    """

    @staticmethod
    def calculate(
        relationships,
        processing_time_ms: Decimal | str | float | int,
    ) -> ReconciliationMetrics:

        relationships = list(relationships)

        confirmed = sum(
            relationship.status
            == RelationshipStatus.CONFIRMED
            for relationship in relationships
        )

        ambiguous = sum(
            relationship.status
            == RelationshipStatus.AMBIGUOUS
            for relationship in relationships
        )

        unresolved = sum(
            relationship.status
            == RelationshipStatus.UNRESOLVED
            for relationship in relationships
        )

        from app.reconciliation.models import (
            MatchMethod,
        )

        ai_assisted = sum(
            relationship.method
            == MatchMethod.AI_ASSISTED
            for relationship in relationships
        )

        return ReconciliationMetrics(
            relationships_processed=len(
                relationships
            ),
            confirmed_relationships=confirmed,
            ambiguous_relationships=ambiguous,
            unresolved_relationships=unresolved,
            ai_assisted_relationships=ai_assisted,
            processing_time_ms=(
                ReconciliationMetricsCalculator
                ._decimal(processing_time_ms)
            ),
        )

    @staticmethod
    def evaluate_precision(
        predicted_relationship_ids: set[str],
        ground_truth_relationship_ids: set[str],
    ) -> Decimal:

        if not predicted_relationship_ids:
            return Decimal("0")

        true_positives = len(
            predicted_relationship_ids
            & ground_truth_relationship_ids
        )

        return (
            Decimal(true_positives)
            / Decimal(len(predicted_relationship_ids))
        )

    @staticmethod
    def evaluate_recall(
        predicted_relationship_ids: set[str],
        ground_truth_relationship_ids: set[str],
    ) -> Decimal:

        if not ground_truth_relationship_ids:
            return Decimal("0")

        true_positives = len(
            predicted_relationship_ids
            & ground_truth_relationship_ids
        )

        return (
            Decimal(true_positives)
            / Decimal(len(ground_truth_relationship_ids))
        )

    @staticmethod
    def with_evaluation(
        metrics: ReconciliationMetrics,
        predicted_relationship_ids: set[str],
        ground_truth_relationship_ids: set[str],
    ) -> ReconciliationMetrics:

        return ReconciliationMetrics(
            relationships_processed=(
                metrics.relationships_processed
            ),
            confirmed_relationships=(
                metrics.confirmed_relationships
            ),
            ambiguous_relationships=(
                metrics.ambiguous_relationships
            ),
            unresolved_relationships=(
                metrics.unresolved_relationships
            ),
            ai_assisted_relationships=(
                metrics.ai_assisted_relationships
            ),
            processing_time_ms=(
                metrics.processing_time_ms
            ),
            relationship_precision=(
                ReconciliationMetricsCalculator
                .evaluate_precision(
                    predicted_relationship_ids,
                    ground_truth_relationship_ids,
                )
            ),
            relationship_recall=(
                ReconciliationMetricsCalculator
                .evaluate_recall(
                    predicted_relationship_ids,
                    ground_truth_relationship_ids,
                )
            ),
        )

    @staticmethod
    def _decimal(value) -> Decimal:

        try:
            return Decimal(str(value))
        except (
            InvalidOperation,
            ValueError,
            TypeError,
        ) as exc:
            raise ValueError(
                "processing_time_ms must be numeric"
            ) from exc


class ReconciliationTimer:
    """
    Small utility for measuring reconciliation throughput.
    """

    def __init__(self):
        self._started_at: float | None = None

    def start(self) -> None:
        self._started_at = perf_counter()

    def elapsed_ms(self) -> Decimal:
        if self._started_at is None:
            raise RuntimeError(
                "Timer has not been started"
            )

        elapsed = (
            perf_counter()
            - self._started_at
        )

        return Decimal(
            str(elapsed * 1000)
        )