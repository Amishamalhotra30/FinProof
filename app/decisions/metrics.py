from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter

from app.decisions.models import (
    DecisionOutcome,
    DecisionResult,
)


@dataclass(frozen=True)
class DecisionMetrics:
    """
    Aggregate metrics for Phase 7 decisions.

    Metrics are observational only. They do not influence
    decision policy or modify financial records.
    """

    total_cases: int
    auto_resolved: int
    pending: int
    human_review: int
    blocked: int

    automation_rate: Decimal
    human_review_rate: Decimal

    false_resolutions: int
    false_resolution_rate: Decimal

    human_agreements: int | None
    human_agreement_rate: Decimal | None

    human_investigation_reduction: Decimal

    unresolved_financial_value: Decimal

    processing_time_ms: Decimal
    throughput: Decimal


class DecisionMetricsCalculator:
    """
    Calculates measurable Phase 7 decision metrics.

    The calculator is deliberately independent from the
    decision policy engine. It only observes completed
    DecisionResult objects.
    """

    def calculate(
        self,
        decisions: list[DecisionResult] | tuple[DecisionResult, ...],
        *,
        ground_truth: dict[str, DecisionOutcome] | None = None,
        human_reviews: dict[str, DecisionOutcome] | None = None,
        processing_time_ms: Decimal | None = None,
    ) -> DecisionMetrics:
        started = perf_counter()

        decision_list = list(decisions)

        total_cases = len(decision_list)

        auto_resolved = self._count(
            decision_list,
            DecisionOutcome.AUTO_RESOLVED,
        )

        pending = self._count(
            decision_list,
            DecisionOutcome.PENDING,
        )

        human_review = self._count_human_review(
            decision_list
        )

        blocked = self._count(
            decision_list,
            DecisionOutcome.BLOCKED,
        )

        automation_rate = self._rate(
            auto_resolved,
            total_cases,
        )

        human_review_rate = self._rate(
            human_review,
            total_cases,
        )

        false_resolutions = self._false_resolutions(
            decision_list,
            ground_truth,
        )

        false_resolution_rate = self._rate(
            false_resolutions,
            total_cases,
        )

        human_agreements, human_agreement_rate = (
            self._human_agreement(
                decision_list,
                human_reviews,
            )
        )

        human_investigation_reduction = (
            self._human_investigation_reduction(
                total_cases,
                human_review,
            )
        )

        unresolved_financial_value = (
            self._unresolved_financial_value(
                decision_list
            )
        )

        elapsed_ms = (
            Decimal(str(
                (perf_counter() - started) * 1000
            ))
        )

        if processing_time_ms is None:
            effective_processing_time = elapsed_ms
        else:
            effective_processing_time = (
                processing_time_ms
            )

        throughput = self._throughput(
            total_cases,
            effective_processing_time,
        )

        return DecisionMetrics(
            total_cases=total_cases,
            auto_resolved=auto_resolved,
            pending=pending,
            human_review=human_review,
            blocked=blocked,
            automation_rate=automation_rate,
            human_review_rate=human_review_rate,
            false_resolutions=false_resolutions,
            false_resolution_rate=false_resolution_rate,
            human_agreements=human_agreements,
            human_agreement_rate=human_agreement_rate,
            human_investigation_reduction=(
                human_investigation_reduction
            ),
            unresolved_financial_value=(
                unresolved_financial_value
            ),
            processing_time_ms=(
                effective_processing_time
            ),
            throughput=throughput,
        )

    @staticmethod
    def _count(
        decisions: list[DecisionResult],
        outcome: DecisionOutcome,
    ) -> int:
        return sum(
            1
            for decision in decisions
            if decision.decision == outcome
        )

    @staticmethod
    def _count_human_review(
        decisions: list[DecisionResult],
    ) -> int:
        return sum(
            1
            for decision in decisions
            if decision.decision
            in {
                DecisionOutcome.HUMAN_REVIEW,
                DecisionOutcome.RESOLVED_WITH_APPROVAL,
            }
        )

    @staticmethod
    def _rate(
        numerator: int,
        denominator: int,
    ) -> Decimal:
        if denominator == 0:
            return Decimal("0")

        return (
            Decimal(numerator)
            / Decimal(denominator)
            * Decimal("100")
        )

    @staticmethod
    def _false_resolutions(
        decisions: list[DecisionResult],
        ground_truth: dict[str, DecisionOutcome] | None,
    ) -> int:
        """
        Counts auto-resolutions that disagree with hidden
        ground truth.

        Ground truth is optional and must never be exposed
        through the production decision result.
        """

        if not ground_truth:
            return 0

        return sum(
            1
            for decision in decisions
            if (
                decision.decision
                == DecisionOutcome.AUTO_RESOLVED
                and decision.case_id in ground_truth
                and decision.decision
                != ground_truth[decision.case_id]
            )
        )

    @staticmethod
    def _human_agreement(
        decisions: list[DecisionResult],
        human_reviews: dict[str, DecisionOutcome] | None,
    ) -> tuple[int | None, Decimal | None]:
        """
        Measures agreement between automated decisions and
        recorded human outcomes.

        Returns None when no human review data is supplied.
        """

        if not human_reviews:
            return None, None

        applicable = [
            decision
            for decision in decisions
            if decision.case_id in human_reviews
        ]

        if not applicable:
            return 0, Decimal("0")

        agreements = sum(
            1
            for decision in applicable
            if decision.decision
            == human_reviews[decision.case_id]
        )

        return (
            agreements,
            DecisionMetricsCalculator._rate(
                agreements,
                len(applicable),
            ),
        )

    @staticmethod
    def _human_investigation_reduction(
        total_cases: int,
        human_review: int,
    ) -> Decimal:
        """
        Percentage of cases that did not require human
        review.

        This is an operational proxy for investigation
        effort reduction.
        """

        if total_cases == 0:
            return Decimal("0")

        automated_or_pending = (
            total_cases - human_review
        )

        return (
            Decimal(automated_or_pending)
            / Decimal(total_cases)
            * Decimal("100")
        )

    @staticmethod
    def _unresolved_financial_value(
        decisions: list[DecisionResult],
    ) -> Decimal:
        """
        Financial value still requiring operational
        attention.

        AUTO_RESOLVED cases are excluded.
        """

        total = Decimal("0")

        for decision in decisions:
            if decision.decision == (
                DecisionOutcome.AUTO_RESOLVED
            ):
                continue

            total += abs(
                decision.financial_impact
            )

        return total

    @staticmethod
    def _throughput(
        total_cases: int,
        processing_time_ms: Decimal,
    ) -> Decimal:
        if total_cases == 0:
            return Decimal("0")

        if processing_time_ms <= 0:
            return Decimal("0")

        return (
            Decimal(total_cases)
            / (
                processing_time_ms
                / Decimal("1000")
            )
        )


def calculate_decision_metrics(
    decisions: list[DecisionResult] | tuple[DecisionResult, ...],
    *,
    ground_truth: dict[str, DecisionOutcome] | None = None,
    human_reviews: dict[str, DecisionOutcome] | None = None,
    processing_time_ms: Decimal | None = None,
) -> DecisionMetrics:
    """
    Convenience wrapper around DecisionMetricsCalculator.
    """

    return DecisionMetricsCalculator().calculate(
        decisions,
        ground_truth=ground_truth,
        human_reviews=human_reviews,
        processing_time_ms=processing_time_ms,
    )