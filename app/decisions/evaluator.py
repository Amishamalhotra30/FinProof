from __future__ import annotations

from decimal import Decimal

from app.decisions.models import (
    DecisionFacts,
    DecisionPolicy,
    DecisionResult,
    MaterialityLevel,
)
from app.decisions.policy import DecisionPolicyEngine
from app.investigation.models import (
    InvestigationResult,
    InvestigationStatus,
)
from app.verification.models import (
    ControlStatus,
    Materiality,
    VerificationResult,
    VerificationStatus,
)


class DecisionEvaluator:
    """
    Phase 7 integration layer.

    Converts Phase 5 verification and optional Phase 6
    investigation results into structured DecisionFacts,
    then delegates the actual decision to the deterministic
    policy engine.

    Responsibilities:
        Phase 5 VerificationResult
              ↓
        Phase 6 InvestigationResult
              ↓
        DecisionFacts
              ↓
        DecisionPolicyEngine
              ↓
        DecisionResult

    This class does not:
        - investigate discrepancies
        - retrieve evidence
        - modify financial records
        - calculate financial corrections
        - call an LLM
    """

    def __init__(
        self,
        policy: DecisionPolicy | None = None,
    ) -> None:
        self.policy_engine = DecisionPolicyEngine(
            policy=policy
        )

    def build_facts(
        self,
        verification: VerificationResult,
        investigation: InvestigationResult | None = None,
    ) -> DecisionFacts:
        """
        Build deterministic DecisionFacts from Phase 5 and
        optional Phase 6 outputs.
        """

        if investigation is not None:
            self._validate_case_identity(
                verification,
                investigation,
            )

        materiality = self._resolve_materiality(
            verification,
            investigation,
        )

        discrepancy_present = bool(
            verification.discrepancies
        )

        financial_impact = self._financial_impact(
            verification,
            investigation,
        )

        explained_amount = (
            abs(investigation.explained_amount)
            if investigation is not None
            else Decimal("0")
        )

        remaining_unexplained = (
            abs(
                investigation.remaining_unexplained
            )
            if investigation is not None
            else self._discrepancy_amount(
                verification
            )
        )

        evidence_sufficient = (
            investigation is not None
            and investigation.status
            == InvestigationStatus.RESOLVED
            and investigation.validated
        )

        contradictory_evidence = (
            investigation is not None
            and investigation.status
            == InvestigationStatus.CONTRADICTION
        )

        human_approval_required = (
            materiality == MaterialityLevel.HIGH
            and self.policy_engine.policy
            .require_human_for_high_materiality
        )

        applicable_controls_passed = (
            verification.status
            == VerificationStatus.VERIFIED
            and not verification.discrepancies
            and all(
                control.status
                in {
                    ControlStatus.PASS,
                    ControlStatus.NOT_APPLICABLE,
                }
                for control in verification.controls
            )
        )

        expected_event_pending = (
            verification.status
            == VerificationStatus.PENDING
        )

        blocking_failure = any(
            discrepancy.blocking
            for discrepancy
            in verification.discrepancies
        ) or any(
            control.blocking
            and control.status == ControlStatus.FAIL
            for control in verification.controls
        )

        investigation_status = (
            investigation.status.value
            if investigation is not None
            else None
        )

        return DecisionFacts(
            case_id=verification.case_id,
            verification_status=(
                verification.status.value
            ),
            investigation_status=investigation_status,
            evidence_sufficient=evidence_sufficient,
            investigation_validated=(
                investigation.validated
                if investigation is not None
                else False
            ),
            contradictory_evidence=(
                contradictory_evidence
            ),
            human_approval_required=(
                human_approval_required
            ),
            financial_impact=financial_impact,
            materiality=materiality,
            explained_amount=explained_amount,
            remaining_unexplained=(
                remaining_unexplained
            ),
            discrepancy_present=(
                discrepancy_present
            ),
            expected_event_pending=(
                expected_event_pending
            ),
            blocking_failure=blocking_failure,
            applicable_controls_passed=(
                applicable_controls_passed
            ),
        )

    def evaluate(
        self,
        verification: VerificationResult,
        investigation: InvestigationResult | None = None,
    ) -> DecisionResult:
        """
        Evaluate one Phase 7 decision.
        """

        facts = self.build_facts(
            verification,
            investigation,
        )

        result = self.policy_engine.evaluate(
            facts
        )

        return self._attach_evidence(
            result,
            investigation,
        )

    # ========================================================
    # MATERIALITY
    # ========================================================

    @staticmethod
    def _resolve_materiality(
        verification: VerificationResult,
        investigation: InvestigationResult | None,
    ) -> MaterialityLevel:
        """
        Convert Phase 5 materiality vocabulary into the
        Phase 7 policy vocabulary.
        """

        levels = [
            discrepancy.materiality
            for discrepancy
            in verification.discrepancies
        ]

        if not levels:
            return MaterialityLevel.NONE

        if Materiality.HIGH in levels:
            return MaterialityLevel.HIGH

        if Materiality.MEDIUM in levels:
            return MaterialityLevel.MEDIUM

        if Materiality.LOW in levels:
            return MaterialityLevel.LOW

        return MaterialityLevel.NONE

    # ========================================================
    # FINANCIAL IMPACT
    # ========================================================

    @staticmethod
    def _financial_impact(
        verification: VerificationResult,
        investigation: InvestigationResult | None,
    ) -> Decimal:
        """
        Determine the financial impact from Phase 5
        discrepancies.

        Investigation does not override the discrepancy's
        financial magnitude.
        """

        if not verification.discrepancies:
            return Decimal("0")

        return sum(
            (
                abs(discrepancy.difference)
                for discrepancy
                in verification.discrepancies
            ),
            Decimal("0"),
        )

    @staticmethod
    def _discrepancy_amount(
        verification: VerificationResult,
    ) -> Decimal:
        """
        Sum absolute Phase 5 discrepancy values.
        """

        return sum(
            (
                abs(discrepancy.difference)
                for discrepancy
                in verification.discrepancies
            ),
            Decimal("0"),
        )

    # ========================================================
    # IDENTITY
    # ========================================================

    @staticmethod
    def _validate_case_identity(
        verification: VerificationResult,
        investigation: InvestigationResult,
    ) -> None:
        """
        Prevent results from different cases being combined.
        """

        if (
            verification.case_id
            != investigation.case_id
        ):
            raise ValueError(
                "Verification and investigation "
                "case IDs do not match."
            )

        if verification.discrepancies:
            discrepancy_ids = {
                discrepancy.discrepancy_id
                for discrepancy
                in verification.discrepancies
            }

            if (
                investigation.discrepancy_id
                not in discrepancy_ids
            ):
                raise ValueError(
                    "Investigation discrepancy ID does not "
                    "belong to the verification result."
                )

    # ========================================================
    # EVIDENCE
    # ========================================================

    @staticmethod
    def _attach_evidence(
        result: DecisionResult,
        investigation: InvestigationResult | None,
    ) -> DecisionResult:
        """
        Carry Phase 6 evidence provenance into the Phase 7
        decision result.

        The evaluator does not create evidence IDs.
        """

        if investigation is None:
            return result

        return result.model_copy(
            update={
                "supporting_evidence_ids": list(
                    investigation.supporting_evidence_ids
                )
            }
        )


def evaluate_decision(
    verification: VerificationResult,
    investigation: InvestigationResult | None = None,
    policy: DecisionPolicy | None = None,
) -> DecisionResult:
    """
    Convenience function for evaluating a Phase 7 case.
    """

    return DecisionEvaluator(
        policy=policy
    ).evaluate(
        verification,
        investigation,
    )


def build_decision_facts(
    verification: VerificationResult,
    investigation: InvestigationResult | None = None,
) -> DecisionFacts:
    """
    Convenience function for constructing DecisionFacts.
    """

    return DecisionEvaluator().build_facts(
        verification,
        investigation,
    )