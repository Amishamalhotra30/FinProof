from dataclasses import dataclass
from decimal import Decimal

from app.decisions.models import (
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResult,
    HumanReviewPackage,
    HumanReviewRecord,
    ReviewAction,
)


class InvalidDecisionAction(ValueError):
    """Raised when an operational action is not permitted."""


@dataclass(frozen=True)
class OperationalAction:
    """
    Bounded operational action produced by Phase 7.

    These actions describe control workflow changes only.
    They never modify financial records or move money.
    """

    case_id: str
    action_type: str
    description: str


class DecisionActionExecutor:
    """
    Execute bounded Phase 7 operational actions.

    This class intentionally does NOT:
        - issue refunds
        - move money
        - modify bank records
        - modify settlements
        - modify source transactions
        - alter financial amounts
        - create missing financial events

    It only translates an already-authorized decision into
    an explicit operational action or human-review record.
    """

    ALLOWED_DECISIONS = frozenset(
        {
            DecisionOutcome.AUTO_RESOLVED,
            DecisionOutcome.PENDING,
            DecisionOutcome.HUMAN_REVIEW,
            DecisionOutcome.RESOLVED_WITH_APPROVAL,
            DecisionOutcome.BLOCKED,
        }
    )

    ALLOWED_REVIEW_ACTIONS = frozenset(
        {
            ReviewAction.APPROVE,
            ReviewAction.REJECT,
            ReviewAction.REQUEST_MORE_EVIDENCE,
        }
    )

    def execute(
        self,
        decision: DecisionResult,
    ) -> OperationalAction:
        """
        Convert a deterministic decision into a bounded
        operational action.

        No financial mutation is performed.
        """

        if decision.decision not in self.ALLOWED_DECISIONS:
            raise InvalidDecisionAction(
                f"Unsupported decision outcome: "
                f"{decision.decision}"
            )

        mapping = {
            DecisionOutcome.AUTO_RESOLVED: (
                "MARK_RESOLVED",
                "Case is marked resolved by policy.",
            ),
            DecisionOutcome.PENDING: (
                "MARK_PENDING",
                "Case remains pending for a future lifecycle event.",
            ),
            DecisionOutcome.HUMAN_REVIEW: (
                "CREATE_HUMAN_REVIEW",
                "Case is routed to human review.",
            ),
            DecisionOutcome.RESOLVED_WITH_APPROVAL: (
                "CREATE_HUMAN_REVIEW",
                "Case is fully explained but requires human approval.",
            ),
            DecisionOutcome.BLOCKED: (
                "BLOCK_CASE",
                "Case is blocked from automatic closure.",
            ),
        }

        action_type, description = mapping[
            decision.decision
        ]

        return OperationalAction(
            case_id=decision.case_id,
            action_type=action_type,
            description=description,
        )

    def create_review_package(
        self,
        decision: DecisionResult,
        *,
        discrepancy_id: str | None = None,
        control_id: str | None = None,
        investigation_status: str | None = None,
        investigation_summary: str | None = None,
        investigation_conclusion: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> HumanReviewPackage:
        """
        Construct the bounded package presented to a human.

        Evidence IDs are references only. This method does not
        retrieve or fabricate evidence.
        """

        if decision.decision not in {
            DecisionOutcome.HUMAN_REVIEW,
            DecisionOutcome.RESOLVED_WITH_APPROVAL,
        }:
            raise InvalidDecisionAction(
                "A human review package can only be created "
                "for HUMAN_REVIEW or RESOLVED_WITH_APPROVAL."
            )

        if evidence_ids is None:
            evidence_ids = list(
                decision.supporting_evidence_ids
            )

        recommended_action = (
            DecisionOutcome.RESOLVED_WITH_APPROVAL
            if decision.decision
            == DecisionOutcome.RESOLVED_WITH_APPROVAL
            else DecisionOutcome.HUMAN_REVIEW
        )

        return HumanReviewPackage(
            case_id=decision.case_id,
            financial_impact=abs(
                decision.financial_impact
            ),
            discrepancy_id=discrepancy_id,
            control_id=control_id,
            investigation_status=investigation_status,
            investigation_summary=(
                investigation_summary
            ),
            investigation_conclusion=(
                investigation_conclusion
            ),
            evidence_ids=list(evidence_ids),
            reason_for_review=self._review_reason(
                decision
            ),
            recommended_action=recommended_action,
        )

    def record_review(
        self,
        decision: DecisionResult,
        action: ReviewAction,
        comment: str,
        *,
        reviewer_id: str | None = None,
    ) -> HumanReviewRecord:
        """
        Record one explicit human review action.

        The record is immutable after construction.
        """

        if decision.decision not in {
            DecisionOutcome.HUMAN_REVIEW,
            DecisionOutcome.RESOLVED_WITH_APPROVAL,
        }:
            raise InvalidDecisionAction(
                "Human review actions are only valid for "
                "human-review decisions."
            )

        if action not in self.ALLOWED_REVIEW_ACTIONS:
            raise InvalidDecisionAction(
                f"Unsupported review action: {action}"
            )

        normalized_comment = comment.strip()

        if not normalized_comment:
            raise InvalidDecisionAction(
                "A human review comment is required."
            )

        reason_code = decision.reason_code

        return HumanReviewRecord(
            case_id=decision.case_id,
            action=action,
            comment=normalized_comment,
            reviewer_id=reviewer_id,
            previous_decision=decision.decision,
            previous_reason_code=reason_code,
            human_override=True,
        )

    @staticmethod
    def _review_reason(
        decision: DecisionResult,
    ) -> str:
        """
        Convert the deterministic reason code into a concise
        human-review explanation.
        """

        reasons = {
            DecisionReasonCode.INSUFFICIENT_EVIDENCE: (
                "Required evidence is insufficient."
            ),
            DecisionReasonCode.CONTRADICTORY_EVIDENCE: (
                "Evidence contains material contradictions."
            ),
            DecisionReasonCode.UNRESOLVED_DISCREPANCY: (
                "The financial discrepancy remains unresolved."
            ),
            DecisionReasonCode.MATERIAL_UNRESOLVED: (
                "A material unresolved control failure prevents closure."
            ),
            DecisionReasonCode.POLICY_REQUIRES_HUMAN: (
                "Configured policy requires human intervention."
            ),
            DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL: (
                "The discrepancy is explained but requires human approval."
            ),
        }

        return reasons.get(
            decision.reason_code,
            "Human review is required by Phase 7 policy.",
        )


def execute_decision(
    decision: DecisionResult,
) -> OperationalAction:
    """
    Convenience function for executing a bounded decision.
    """

    return DecisionActionExecutor().execute(
        decision
    )


def create_human_review_package(
    decision: DecisionResult,
    **kwargs,
) -> HumanReviewPackage:
    """
    Convenience function for constructing a review package.
    """

    return DecisionActionExecutor().create_review_package(
        decision,
        **kwargs,
    )


def record_human_review(
    decision: DecisionResult,
    action: ReviewAction,
    comment: str,
    *,
    reviewer_id: str | None = None,
) -> HumanReviewRecord:
    """
    Convenience function for recording human review.
    """

    return DecisionActionExecutor().record_review(
        decision,
        action,
        comment,
        reviewer_id=reviewer_id,
    )