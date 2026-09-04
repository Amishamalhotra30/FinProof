from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from app.decisions.models import (
    BatchControlResult,
    BatchControlStatus,
    DecisionOutcome,
    DecisionResult,
)


class BatchDecisionController:
    """
    Aggregate individual Phase 7 decisions into a batch-level
    financial control status.

    This class does not:
        - recalculate individual decisions
        - override policy decisions
        - modify financial records
        - move money
        - resolve discrepancies
        - call an LLM

    It only determines the operational status of the batch from
    already-authoritative case decisions.
    """

    def evaluate(
        self,
        batch_id: str,
        decisions: Iterable[DecisionResult],
    ) -> BatchControlResult:
        """
        Evaluate the overall control state of a batch.
        """

        decision_list = list(decisions)

        self._validate_case_ids(decision_list)

        total_cases = len(decision_list)

        auto_resolved = sum(
            decision.decision
            == DecisionOutcome.AUTO_RESOLVED
            for decision in decision_list
        )

        pending = sum(
            decision.decision
            == DecisionOutcome.PENDING
            for decision in decision_list
        )

        human_review = sum(
            decision.decision
            in {
                DecisionOutcome.HUMAN_REVIEW,
                DecisionOutcome.RESOLVED_WITH_APPROVAL,
            }
            for decision in decision_list
        )

        blocked = sum(
            decision.decision
            == DecisionOutcome.BLOCKED
            for decision in decision_list
        )

        unresolved_financial_value = sum(
            (
                abs(decision.financial_impact)
                for decision in decision_list
                if decision.decision
                in {
                    DecisionOutcome.PENDING,
                    DecisionOutcome.HUMAN_REVIEW,
                    DecisionOutcome.RESOLVED_WITH_APPROVAL,
                    DecisionOutcome.BLOCKED,
                }
            ),
            Decimal("0"),
        )

        final_status = self._determine_batch_status(
            total_cases=total_cases,
            auto_resolved=auto_resolved,
            pending=pending,
            human_review=human_review,
            blocked=blocked,
        )

        return BatchControlResult(
            batch_id=batch_id,
            total_cases=total_cases,
            auto_resolved=auto_resolved,
            pending=pending,
            human_review=human_review,
            blocked=blocked,
            unresolved_financial_value=(
                unresolved_financial_value
            ),
            final_control_status=final_status,
        )

    @staticmethod
    def _determine_batch_status(
        *,
        total_cases: int,
        auto_resolved: int,
        pending: int,
        human_review: int,
        blocked: int,
    ) -> BatchControlStatus:
        """
        Determine the strongest required batch disposition.

        Priority:

            BLOCKED
                ↓
            REVIEW_REQUIRED
                ↓
            READY_WITH_NON_MATERIAL_EXCEPTIONS
                ↓
            READY_TO_CLOSE
        """

        if blocked > 0:
            return BatchControlStatus.BLOCKED

        if human_review > 0:
            return BatchControlStatus.REVIEW_REQUIRED

        if pending > 0:
            return (
                BatchControlStatus
                .READY_WITH_NON_MATERIAL_EXCEPTIONS
            )

        if total_cases == auto_resolved:
            return BatchControlStatus.READY_TO_CLOSE

        return (
            BatchControlStatus
            .READY_WITH_NON_MATERIAL_EXCEPTIONS
        )

    @staticmethod
    def _validate_case_ids(
        decisions: list[DecisionResult],
    ) -> None:
        """
        Ensure every decision belongs to a distinct case.

        Duplicate case decisions would make batch aggregation
        ambiguous and could distort control totals.
        """

        case_ids = [
            decision.case_id
            for decision in decisions
        ]

        if len(case_ids) != len(set(case_ids)):
            raise ValueError(
                "Batch contains duplicate case decisions."
            )


def evaluate_batch_decisions(
    batch_id: str,
    decisions: Iterable[DecisionResult],
) -> BatchControlResult:
    """
    Convenience function for batch-level control evaluation.
    """

    return BatchDecisionController().evaluate(
        batch_id,
        decisions,
    )