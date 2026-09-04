from decimal import Decimal

from app.decisions.models import (
    DecisionFacts,
    DecisionOutcome,
    DecisionPolicy,
    DecisionReasonCode,
    DecisionResult,
    MaterialityLevel,
)


class DecisionPolicyEngine:
    """
    Deterministic Phase 7 control-decision policy.

    The policy engine consumes structured decision facts and
    produces a bounded operational decision.

    It does not:
        - retrieve evidence
        - investigate discrepancies
        - modify financial records
        - call an LLM
        - use confidence scores
    """

    def __init__(
        self,
        policy: DecisionPolicy | None = None,
    ):
        self.policy = policy or DecisionPolicy()
        self.policy.validate_configuration()

    def evaluate(
        self,
        facts: DecisionFacts,
    ) -> DecisionResult:
        """
        Evaluate one case using deterministic policy rules.
        """

        # --------------------------------------------------------
        # P7-R1: All applicable controls passed
        # --------------------------------------------------------

        if facts.applicable_controls_passed:
            return self._auto_resolve_verified(
                facts
            )

        # --------------------------------------------------------
        # P7-R2: Expected event pending
        # --------------------------------------------------------

        if facts.expected_event_pending:
            return self._pending(
                facts
            )

        # --------------------------------------------------------
        # Contradictory evidence
        # --------------------------------------------------------

        if facts.contradictory_evidence:
            return self._human_review(
                facts,
                DecisionReasonCode.CONTRADICTORY_EVIDENCE,
                "Contradictory evidence prevents safe automatic resolution.",
            )

        # --------------------------------------------------------
        # Insufficient evidence
        # --------------------------------------------------------

        if (
            facts.investigation_status
            == "INSUFFICIENT_EVIDENCE"
        ):
            return self._human_review(
                facts,
                DecisionReasonCode.INSUFFICIENT_EVIDENCE,
                "Required evidence is insufficient for safe automatic resolution.",
            )

        # --------------------------------------------------------
        # Fully resolved investigation
        # --------------------------------------------------------

        if (
            facts.investigation_status == "RESOLVED"
            and facts.investigation_validated
            and facts.evidence_sufficient
            and facts.remaining_unexplained
            == Decimal("0")
        ):
            return self._evaluate_resolved(
                facts
            )

        # --------------------------------------------------------
        # UNRESOLVED INVESTIGATION
        #
        # A HIGH materiality unresolved case is BLOCKED only
        # when the verification/control layer explicitly marks
        # the failure as blocking.
        #
        # This preserves the distinction between:
        #
        #   HIGH + unresolved + non-blocking -> HUMAN_REVIEW
        #   HIGH + unresolved + blocking     -> BLOCKED
        # --------------------------------------------------------

        if facts.investigation_status == "UNRESOLVED":

            if (
                facts.blocking_failure
                and facts.materiality == MaterialityLevel.HIGH
                and self.policy.block_material_unresolved
            ):
                return self._blocked(
                    facts
                )

            return self._human_review(
                facts,
                DecisionReasonCode.UNRESOLVED_DISCREPANCY,
                "The discrepancy remains unresolved.",
            )

        # --------------------------------------------------------
        # Existing blocking failure rule
        #
        # Handles blocking failures that are not represented
        # by an UNRESOLVED investigation.
        # --------------------------------------------------------

        if facts.blocking_failure:
            return self._blocked(
                facts
            )

        # --------------------------------------------------------
        # Contradiction
        # --------------------------------------------------------

        if facts.investigation_status == "CONTRADICTION":
            return self._human_review(
                facts,
                DecisionReasonCode.CONTRADICTORY_EVIDENCE,
                "Contradictory evidence prevents safe automatic resolution.",
            )

        # --------------------------------------------------------
        # Default policy fallback
        # --------------------------------------------------------

        return self._human_review(
            facts,
            DecisionReasonCode.POLICY_REQUIRES_HUMAN,
            "The case cannot be safely resolved automatically under the configured policy.",
        )

    # ========================================================
    # VERIFIED CASE
    # ========================================================

    def _auto_resolve_verified(
        self,
        facts: DecisionFacts,
    ) -> DecisionResult:
        if not self.policy.allow_verified_auto_resolution:
            return self._human_review(
                facts,
                DecisionReasonCode.POLICY_REQUIRES_HUMAN,
                "Verified cases require human handling under the configured policy.",
            )

        return self._result(
            facts=facts,
            decision=DecisionOutcome.AUTO_RESOLVED,
            reason_code=DecisionReasonCode.ALL_CONTROLS_PASSED,
            rule_id="P7-R1",
            basis=[
                "All applicable deterministic controls passed.",
                "No discrepancy requires investigation.",
            ],
        )

    # ========================================================
    # PENDING
    # ========================================================

    def _pending(
        self,
        facts: DecisionFacts,
    ) -> DecisionResult:
        return self._result(
            facts=facts,
            decision=DecisionOutcome.PENDING,
            reason_code=DecisionReasonCode.EXPECTED_EVENT_PENDING,
            rule_id="P7-R2",
            basis=[
                "An expected lifecycle event is not yet complete.",
                "The case should remain open for a later verification cycle.",
            ],
        )

    # ========================================================
    # FULLY RESOLVED
    # ========================================================

    def _evaluate_resolved(
        self,
        facts: DecisionFacts,
    ) -> DecisionResult:

        financial_impact = abs(
            facts.financial_impact
        )

        # --------------------------------------------------------
        # P7-R5: Explicit human approval requirement
        # --------------------------------------------------------

        if facts.human_approval_required:
            return self._result(
                facts=facts,
                decision=(
                    DecisionOutcome.RESOLVED_WITH_APPROVAL
                ),
                reason_code=(
                    DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL
                ),
                rule_id="P7-R5",
                basis=[
                    "The investigation fully explains the discrepancy.",
                    "The investigation result passed deterministic validation.",
                    "Evidence is sufficient.",
                    "Configured policy requires human approval.",
                ],
            )

        # --------------------------------------------------------
        # P7-R6: Materiality requires human approval
        # --------------------------------------------------------

        if (
            facts.materiality == MaterialityLevel.HIGH
            or (
                facts.materiality == MaterialityLevel.MEDIUM
                and self.policy.require_human_for_medium_materiality
            )
        ):
            return self._result(
                facts=facts,
                decision=(
                    DecisionOutcome.RESOLVED_WITH_APPROVAL
                ),
                reason_code=(
                    DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL
                ),
                rule_id="P7-R6",
                basis=[
                    "The investigation fully explains the discrepancy.",
                    "The financial impact is material under policy.",
                    "Human approval is required before closure.",
                ],
            )

        # --------------------------------------------------------
        # P7-R7: High materiality explicit policy rule
        # --------------------------------------------------------

        if (
            facts.materiality == MaterialityLevel.HIGH
            and self.policy.require_human_for_high_materiality
        ):
            return self._result(
                facts=facts,
                decision=(
                    DecisionOutcome.RESOLVED_WITH_APPROVAL
                ),
                reason_code=(
                    DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL
                ),
                rule_id="P7-R7",
                basis=[
                    "The investigation fully explains the discrepancy.",
                    "The financial impact is high materiality.",
                    "Configured policy requires human approval.",
                ],
            )

        # --------------------------------------------------------
        # P7-R4: Fully explained and below auto-resolution
        # threshold
        # --------------------------------------------------------

        if (
            financial_impact
            <= self.policy.auto_resolution_threshold
            and self.policy.allow_non_material_auto_resolution
        ):
            return self._result(
                facts=facts,
                decision=DecisionOutcome.AUTO_RESOLVED,
                reason_code=(
                    DecisionReasonCode.FULLY_EXPLAINED_NON_MATERIAL
                ),
                rule_id="P7-R4",
                basis=[
                    "The investigation fully explains the discrepancy.",
                    "The investigation result passed deterministic validation.",
                    "No contradictory evidence remains.",
                    "Financial impact is within the automatic-resolution threshold.",
                ],
            )

        # --------------------------------------------------------
        # P7-R8: Fully explained but above auto threshold
        # --------------------------------------------------------

        return self._result(
            facts=facts,
            decision=(
                DecisionOutcome.RESOLVED_WITH_APPROVAL
            ),
            reason_code=(
                DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL
            ),
            rule_id="P7-R8",
            basis=[
                "The investigation fully explains the discrepancy.",
                "The financial impact exceeds the automatic-resolution threshold.",
                "Human approval is required.",
            ],
        )

    # ========================================================
    # BLOCKED
    # ========================================================

    def _blocked(
        self,
        facts: DecisionFacts,
    ) -> DecisionResult:

        if self.policy.block_material_unresolved:
            return self._result(
                facts=facts,
                decision=DecisionOutcome.BLOCKED,
                reason_code=(
                    DecisionReasonCode.MATERIAL_UNRESOLVED
                ),
                rule_id="P7-R9",
                basis=[
                    "The discrepancy remains unresolved.",
                    "The failure is explicitly marked as blocking.",
                    "Configured policy does not permit closing the case.",
                ],
            )

        return self._human_review(
            facts,
            DecisionReasonCode.POLICY_REQUIRES_HUMAN,
            "Blocking policy is disabled; human review is required.",
        )

    # ========================================================
    # HUMAN REVIEW
    # ========================================================

    def _human_review(
        self,
        facts: DecisionFacts,
        reason_code: DecisionReasonCode,
        reason: str,
    ) -> DecisionResult:
        return self._result(
            facts=facts,
            decision=DecisionOutcome.HUMAN_REVIEW,
            reason_code=reason_code,
            rule_id="P7-R10",
            basis=[
                reason,
                "Automatic financial resolution is not authorized.",
            ],
        )

    # ========================================================
    # RESULT BUILDER
    # ========================================================

    @staticmethod
    def _result(
        facts: DecisionFacts,
        decision: DecisionOutcome,
        reason_code: DecisionReasonCode,
        rule_id: str,
        basis: list[str],
    ) -> DecisionResult:
        return DecisionResult(
            case_id=facts.case_id,
            decision=decision,
            reason_code=reason_code,
            basis=basis,
            financial_impact=abs(
                facts.financial_impact
            ),
            materiality=facts.materiality,
            policy_rule_id=rule_id,
            evidence_sufficient=(
                facts.evidence_sufficient
            ),
            investigation_validated=(
                facts.investigation_validated
            ),
            contradictory_evidence=(
                facts.contradictory_evidence
            ),
        )


def evaluate_decision(
    facts: DecisionFacts,
    policy: DecisionPolicy | None = None,
) -> DecisionResult:
    """
    Convenience function for evaluating one decision.
    """

    return DecisionPolicyEngine(
        policy=policy
    ).evaluate(facts)