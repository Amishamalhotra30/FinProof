from decimal import Decimal

from app.investigation.models import (
    EvidenceRelation,
    HypothesisStatus,
    HypothesisType,
    InvestigationCase,
    InvestigationEvidence,
    InvestigationHypothesis,
    HypothesisFinding,
)


class HypothesisEvaluator:
    """
    Deterministically evaluates one investigation hypothesis
    against retrieved investigation evidence.

    This component does not:
        - retrieve evidence
        - generate hypotheses
        - invent evidence
        - use an LLM
        - modify the investigation case

    It only evaluates the relationship between an existing
    hypothesis and supplied evidence.
    """

    def evaluate(
        self,
        case: InvestigationCase,
        hypothesis: InvestigationHypothesis,
        evidence: list[InvestigationEvidence],
    ) -> HypothesisFinding:
        """
        Evaluate one hypothesis against supplied evidence.

        Evidence is classified according to its already-established
        relationship with the hypothesis.

        No evidence is considered supporting merely because it was
        retrieved.
        """

        supporting_ids: list[str] = []
        contradicting_ids: list[str] = []

        explained_amount = Decimal("0")

        for item in evidence:

            if item.relationship == EvidenceRelation.SUPPORTS:
                supporting_ids.append(item.evidence_id)

                if item.amount is not None:
                    explained_amount += abs(item.amount)

            elif (
                item.relationship
                == EvidenceRelation.CONTRADICTS
            ):
                contradicting_ids.append(
                    item.evidence_id
                )

        status = self._determine_status(
            supporting_ids=supporting_ids,
            contradicting_ids=contradicting_ids,
            explained_amount=explained_amount,
            case=case,
            hypothesis=hypothesis,
        )

        reasoning = self._build_reasoning(
            status=status,
            hypothesis_type=hypothesis.hypothesis_type,
            supporting_count=len(supporting_ids),
            contradicting_count=len(
                contradicting_ids
            ),
            explained_amount=explained_amount,
        )

        return HypothesisFinding(
            hypothesis_type=hypothesis.hypothesis_type,
            status=status,
            explained_amount=explained_amount,
            evidence_ids=supporting_ids,
            contradicting_evidence_ids=(
                contradicting_ids
            ),
            reasoning=reasoning,
        )

    @staticmethod
    def _determine_status(
        *,
        supporting_ids: list[str],
        contradicting_ids: list[str],
        explained_amount: Decimal,
        case: InvestigationCase,
        hypothesis: InvestigationHypothesis,
    ) -> HypothesisStatus:
        """
        Determine hypothesis status from explicit evidence.

        Priority:

        1. Contradicted
           Contradicting evidence exists and no supporting
           evidence establishes the hypothesis.

        2. Supported
           Supporting evidence explains the discrepancy.

        3. Weakly supported
           Supporting evidence exists but does not explain
           the complete discrepancy.

        4. Undetermined
           No relevant evidence exists.

        5. Unsupported
           Reserved for explicit negative evidence without
           enough information to classify as contradiction.
        """

        if (
            contradicting_ids
            and not supporting_ids
        ):
            return HypothesisStatus.CONTRADICTED

        if supporting_ids:

            target_amount = abs(
                case.difference
            )

            if target_amount == Decimal("0"):
                return HypothesisStatus.SUPPORTED

            if explained_amount >= target_amount:
                return HypothesisStatus.SUPPORTED

            return HypothesisStatus.WEAKLY_SUPPORTED

        return HypothesisStatus.UNDETERMINED

    @staticmethod
    def _build_reasoning(
        *,
        status: HypothesisStatus,
        hypothesis_type: HypothesisType,
        supporting_count: int,
        contradicting_count: int,
        explained_amount: Decimal,
    ) -> str:
        """
        Build deterministic human-readable reasoning.

        The text describes the evidence state only. It does not
        claim an unverified root cause.
        """

        if status == HypothesisStatus.SUPPORTED:
            return (
                f"{hypothesis_type.value} is supported by "
                f"{supporting_count} evidence item(s), "
                f"explaining {explained_amount} of the "
                f"discrepancy."
            )

        if status == HypothesisStatus.WEAKLY_SUPPORTED:
            return (
                f"{hypothesis_type.value} has supporting "
                f"evidence, but the retrieved evidence "
                f"explains only {explained_amount} of the "
                f"discrepancy."
            )

        if status == HypothesisStatus.CONTRADICTED:
            return (
                f"{hypothesis_type.value} is contradicted "
                f"by {contradicting_count} evidence item(s)."
            )

        if status == HypothesisStatus.UNSUPPORTED:
            return (
                f"{hypothesis_type.value} has insufficient "
                f"supporting evidence."
            )

        return (
            f"No decisive evidence was retrieved for "
            f"{hypothesis_type.value}."
        )


def evaluate_hypothesis(
    case: InvestigationCase,
    hypothesis: InvestigationHypothesis,
    evidence: list[InvestigationEvidence],
) -> HypothesisFinding:
    """
    Convenience function for evaluating one hypothesis.
    """

    return HypothesisEvaluator().evaluate(
        case,
        hypothesis,
        evidence,
    )


def evaluate_hypotheses(
    case: InvestigationCase,
    hypotheses: list[InvestigationHypothesis],
    evidence_by_hypothesis: dict[
        str,
        list[InvestigationEvidence],
    ],
) -> list[HypothesisFinding]:
    """
    Evaluate multiple hypotheses.

    Evidence is supplied explicitly per hypothesis so that
    evidence retrieval and hypothesis evaluation remain
    separate responsibilities.
    """

    evaluator = HypothesisEvaluator()

    findings: list[HypothesisFinding] = []

    for hypothesis in hypotheses:

        evidence = evidence_by_hypothesis.get(
            hypothesis.hypothesis_id,
            [],
        )

        findings.append(
            evaluator.evaluate(
                case,
                hypothesis,
                evidence,
            )
        )

    return findings
