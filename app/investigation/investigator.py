from decimal import Decimal

from app.domain.graph import EventGraph
from app.investigation.evidence_retriever import (
    EvidenceRetriever,
)
from app.investigation.hypotheses import (
    HypothesisGenerator,
)
from app.investigation.hypothesis_evaluator import (
    HypothesisEvaluator,
)
from app.investigation.models import (
    EvidenceRelation,
    HypothesisStatus,
    InvestigationCase,
    InvestigationResult,
    InvestigationStatus,
)


class InvestigationOrchestrator:
    """
    Coordinates the complete deterministic Phase 6
    investigation workflow.

    Pipeline:

        InvestigationCase
            ↓
        HypothesisGenerator
            ↓
        EvidenceRetriever
            ↓
        HypothesisEvaluator
            ↓
        Evidence/Amount Normalization
            ↓
        InvestigationResult

    Result validation is intentionally a separate operation.

    The orchestrator does not:
        - invent hypotheses
        - invent evidence
        - infer unsupported financial facts
        - modify the investigation case
        - repair financial records
        - make financial corrections
        - use an LLM
    """

    def __init__(
        self,
        hypothesis_generator: HypothesisGenerator | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
        hypothesis_evaluator: HypothesisEvaluator | None = None,
    ):
        self.hypothesis_generator = (
            hypothesis_generator
            or HypothesisGenerator()
        )

        self.evidence_retriever = (
            evidence_retriever
            or EvidenceRetriever()
        )

        self.hypothesis_evaluator = (
            hypothesis_evaluator
            or HypothesisEvaluator()
        )

    # ========================================================
    # MAIN INVESTIGATION
    # ========================================================

    def investigate(
        self,
        case: InvestigationCase,
        graph: EventGraph,
    ) -> InvestigationResult:
        """
        Run the complete Phase 6 investigation for one case.

        The important invariant enforced here is:

            one supporting evidence item
            -> one supporting hypothesis finding

        Evidence may be retrieved for multiple hypotheses, but
        it may contribute financially to the final investigation
        only once.

        The final aggregate explanation is also capped at the
        absolute discrepancy.

        The returned InvestigationResult is marked validated=False.

        Validation is performed separately by
        InvestigationResultValidator.
        """

        # ----------------------------------------------------
        # STEP 1 — Generate bounded hypotheses
        # ----------------------------------------------------

        hypotheses = (
            self.hypothesis_generator.generate(
                case
            )
        )

        # ----------------------------------------------------
        # STEP 2 — Retrieve and evaluate hypotheses
        # ----------------------------------------------------

        raw_findings = []

        evidence_by_hypothesis = {}

        for hypothesis in hypotheses:

            evidence = (
                self.evidence_retriever
                .retrieve_for_hypothesis(
                    case,
                    hypothesis,
                    graph,
                )
            )

            evidence_by_hypothesis[
                hypothesis.hypothesis_id
            ] = evidence

            finding = (
                self.hypothesis_evaluator.evaluate(
                    case,
                    hypothesis,
                    evidence,
                )
            )

            raw_findings.append(
                (
                    hypothesis,
                    finding,
                    evidence,
                )
            )

        # ----------------------------------------------------
        # STEP 3 — Normalize findings
        # ----------------------------------------------------

        findings = self._normalize_findings(
            raw_findings=raw_findings,
            case=case,
        )

        # ----------------------------------------------------
        # STEP 4 — Calculate explained amount
        # ----------------------------------------------------

        explained_amount = self._explained_amount(
            findings=findings,
            evidence_by_hypothesis=(
                evidence_by_hypothesis
            ),
            case=case,
        )

        print("\n========== EXPLAINED AMOUNT DEBUG ==========")
        print("CASE:", case.case_id)
        print("TARGET:", abs(case.difference))
        print("CALCULATED EXPLAINED:", explained_amount)

        print("FINDING IDS:")
        for finding in findings:
            print(
                finding.hypothesis_type.value,
                finding.status.value,
                finding.evidence_ids,
                finding.explained_amount,
            )

        print("EVIDENCE LOOKUP:")
        for evidence_list in evidence_by_hypothesis.values():
            for evidence in evidence_list:
                if evidence.evidence_id in {
                    eid
                    for finding in findings
                    for eid in finding.evidence_ids
                }:
                    print(
                        evidence.evidence_id,
                        "| REL=", evidence.relationship,
                        "| AMOUNT=", evidence.amount,
                        "| TYPE=", type(evidence.amount),
                    )

        print("============================================")
        print("\n========== NORMALIZATION DEBUG ==========")
        print("CASE:", case.case_id)
        print("CONTROL:", case.control_failure)
        print("DIFFERENCE:", case.difference)

        print("\nRAW FINDINGS:")
        for _, finding, evidence in raw_findings:
            print(
                finding.hypothesis_type.value,
                "| STATUS:", finding.status.value,
                "| EXPLAINED:", finding.explained_amount,
                "| IDS:", finding.evidence_ids,
            )

        print("\nNORMALIZED FINDINGS:")
        for finding in findings:
            print(
                finding.hypothesis_type.value,
                "| STATUS:", finding.status.value,
                "| EXPLAINED:", finding.explained_amount,
                "| IDS:", finding.evidence_ids,
            )

        print("=========================================\n")

        # ----------------------------------------------------
        # STEP 5 — Calculate remaining unexplained amount
        # ----------------------------------------------------

        discrepancy = abs(
            case.difference
        )

        remaining_unexplained = (
            discrepancy
            - explained_amount
        )

        if remaining_unexplained < Decimal("0"):
            remaining_unexplained = Decimal("0")

        # ----------------------------------------------------
        # STEP 6 — Collect supporting evidence
        # ----------------------------------------------------

        supporting_evidence_ids = (
            self._supporting_evidence_ids(
                findings
            )
        )

        # ----------------------------------------------------
        # STEP 7 — Determine overall status
        # ----------------------------------------------------

        status = self._determine_status(
            case=case,
            findings=findings,
            explained_amount=explained_amount,
            remaining_unexplained=(
                remaining_unexplained
            ),
        )

        # ----------------------------------------------------
        # STEP 8 — Build deterministic conclusion
        # ----------------------------------------------------

        conclusion = self._build_conclusion(
            status=status,
            explained_amount=explained_amount,
            remaining_unexplained=(
                remaining_unexplained
            ),
        )

        # ----------------------------------------------------
        # STEP 9 — Stable investigation identifier
        # ----------------------------------------------------

        investigation_id = (
            f"INV_{case.case_id}_"
            f"{case.discrepancy_id}"
        )

        # ----------------------------------------------------
        # STEP 10 — Build result
        # ----------------------------------------------------

        return InvestigationResult(
            investigation_id=investigation_id,
            case_id=case.case_id,
            discrepancy_id=case.discrepancy_id,
            status=status,
            hypotheses=findings,
            explained_amount=explained_amount,
            remaining_unexplained=(
                remaining_unexplained
            ),
            supporting_evidence_ids=(
                supporting_evidence_ids
            ),
            conclusion=conclusion,
            validated=False,
        )

    # ========================================================
    # FINDING NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_findings(
        *,
        raw_findings,
        case: InvestigationCase,
    ):
        """
        Normalize independently evaluated hypothesis findings.

        Rules:

        1. A supporting evidence ID may belong to only one
           hypothesis finding.

        2. Evidence is assigned deterministically in hypothesis
           generation order.

        3. A finding's explained amount is recalculated from
           the evidence that remains assigned to it.

        4. A finding's explained amount can never exceed the
           absolute discrepancy.

        5. Contradicting evidence remains attached to the
           appropriate finding.

        6. A hypothesis that loses all of its supporting
           evidence is not allowed to remain falsely marked
           as SUPPORTED/WEAKLY_SUPPORTED.
        """

        discrepancy = abs(
            case.difference
        )

        used_supporting_evidence: set[str] = set()

        normalized = []

        for hypothesis, finding, evidence in raw_findings:

            # ------------------------------------------------
            # Determine which evidence is genuinely supporting
            # ------------------------------------------------

            evidence_by_id = {
                item.evidence_id: item
                for item in evidence
            }

            retained_supporting_ids: list[str] = []

            for evidence_id in finding.evidence_ids:

                if evidence_id in used_supporting_evidence:
                    continue

                item = evidence_by_id.get(
                    evidence_id
                )

                if item is None:
                    continue

                if (
                    item.relationship
                    != EvidenceRelation.SUPPORTS
                ):
                    continue

                used_supporting_evidence.add(
                    evidence_id
                )

                retained_supporting_ids.append(
                    evidence_id
                )

            # ------------------------------------------------
            # Recalculate this hypothesis's explanation
            # from uniquely assigned evidence.
            # ------------------------------------------------

            explained_amount = Decimal("0")

            for evidence_id in (
                retained_supporting_ids
            ):

                item = evidence_by_id.get(
                    evidence_id
                )

                if item is None:
                    continue

                if item.amount is None:
                    continue

                explained_amount += abs(
                    item.amount
                )

            # ------------------------------------------------
            # Never allow a single finding to exceed the
            # discrepancy.
            # ------------------------------------------------

            if explained_amount > discrepancy:
                explained_amount = discrepancy

            # ------------------------------------------------
            # Determine normalized status.
            #
            # If evidence was removed because another
            # hypothesis already owns it, this hypothesis
            # cannot continue claiming support.
            # ------------------------------------------------

            contradicting_ids = list(
                finding.contradicting_evidence_ids
            )

            if retained_supporting_ids:

                if discrepancy == Decimal("0"):
                    normalized_status = (
                        HypothesisStatus.SUPPORTED
                    )

                elif (
                    explained_amount
                    >= discrepancy
                ):
                    normalized_status = (
                        HypothesisStatus.SUPPORTED
                    )

                else:
                    normalized_status = (
                        HypothesisStatus.WEAKLY_SUPPORTED
                    )

            elif contradicting_ids:

                normalized_status = (
                    HypothesisStatus.CONTRADICTED
                )

            else:

                normalized_status = (
                    HypothesisStatus.UNDETERMINED
                )

            # ------------------------------------------------
            # Rebuild reasoning deterministically.
            # ------------------------------------------------

            reasoning = (
                HypothesisEvaluator._build_reasoning(
                    status=normalized_status,
                    hypothesis_type=(
                        finding.hypothesis_type
                    ),
                    supporting_count=len(
                        retained_supporting_ids
                    ),
                    contradicting_count=len(
                        contradicting_ids
                    ),
                    explained_amount=(
                        explained_amount
                    ),
                )
            )

            normalized.append(
                finding.model_copy(
                    update={
                        "status": normalized_status,
                        "explained_amount": (
                            explained_amount
                        ),
                        "evidence_ids": (
                            retained_supporting_ids
                        ),
                        "contradicting_evidence_ids": (
                            contradicting_ids
                        ),
                        "reasoning": reasoning,
                    }
                )
            )

        return normalized

    # ========================================================
    # EXPLAINED AMOUNT
    # ========================================================

    @staticmethod
    def _explained_amount(
        *,
        findings,
        evidence_by_hypothesis,
        case: InvestigationCase,
    ) -> Decimal:
        """
        Calculate the financial amount explained by normalized
        hypothesis findings.

        Normalization has already determined the financially
        explained amount for each finding from its uniquely
        assigned supporting evidence.

        Therefore this method aggregates the normalized
        finding.explained_amount values instead of re-summing
        raw evidence.amount values.

        The same evidence may have been retrieved for multiple
        hypotheses, but normalized findings ensure that it is
        financially counted only once.

        The aggregate explanation is capped at the absolute
        discrepancy.
        """

        target = abs(
            case.difference
        )

        # Structural discrepancies have no monetary amount
        # to explain.
        if target == Decimal("0"):
            return Decimal("0")

        total = Decimal("0")

        seen_evidence_ids: set[str] = set()

        for finding in findings:

            if finding.status not in {
                HypothesisStatus.SUPPORTED,
                HypothesisStatus.WEAKLY_SUPPORTED,
            }:
                continue

            # A normalized finding without supporting evidence
            # cannot contribute financially.
            if not finding.evidence_ids:
                continue

            # Only count the amount associated with evidence
            # that this normalized finding uniquely owns.
            new_evidence_ids = [
                evidence_id
                for evidence_id in finding.evidence_ids
                if evidence_id not in seen_evidence_ids
            ]

            if not new_evidence_ids:
                continue

            finding_amount = (
                finding.explained_amount
            )

            if finding_amount <= Decimal("0"):
                continue

            total += finding_amount

            seen_evidence_ids.update(
                new_evidence_ids
            )

            if total >= target:
                return target

        return min(
            total,
            target,
        )

    # ========================================================
    # SUPPORTING EVIDENCE
    # ========================================================

    @staticmethod
    def _supporting_evidence_ids(
        findings,
    ) -> list[str]:
        """
        Collect unique supporting evidence IDs in deterministic
        first-seen order.

        Individual findings have already been normalized, so
        duplication should not occur here. The defensive
        uniqueness check remains intentionally in place.
        """

        result: list[str] = []

        seen: set[str] = set()

        for finding in findings:

            if finding.status not in {
                HypothesisStatus.SUPPORTED,
                HypothesisStatus.WEAKLY_SUPPORTED,
            }:
                continue

            for evidence_id in (
                finding.evidence_ids
            ):

                if evidence_id in seen:
                    continue

                seen.add(
                    evidence_id
                )

                result.append(
                    evidence_id
                )

        return result

    # ========================================================
    # STATUS
    # ========================================================

    @staticmethod
    def _determine_status(
        *,
        case: InvestigationCase,
        findings,
        explained_amount: Decimal,
        remaining_unexplained: Decimal,
    ) -> InvestigationStatus:
        """
        Determine the overall investigation status.

        RESOLVED:
            The complete discrepancy is explained.

        UNRESOLVED:
            Supporting evidence exists, but some amount
            remains unexplained.

        CONTRADICTION:
            Candidate explanations are contradicted and
            no supporting explanation exists.

        INSUFFICIENT_EVIDENCE:
            No hypothesis has supporting evidence.

        IN_PROGRESS:
            Reserved for future asynchronous workflows.
        """

        discrepancy = abs(
            case.difference
        )

        has_contradiction = any(
            finding.status
            == HypothesisStatus.CONTRADICTED
            for finding in findings
        )

        has_support = any(
            finding.status
            in {
                HypothesisStatus.SUPPORTED,
                HypothesisStatus.WEAKLY_SUPPORTED,
            }
            and finding.evidence_ids
            for finding in findings
        )

        # ----------------------------------------------------
        # Complete explanation.
        # ----------------------------------------------------

        if (
            explained_amount
            >= discrepancy
            and remaining_unexplained
            == Decimal("0")
        ):
            return InvestigationStatus.RESOLVED

        # ----------------------------------------------------
        # Partial explanation.
        # ----------------------------------------------------

        if has_support:
            return InvestigationStatus.UNRESOLVED

        # ----------------------------------------------------
        # Contradiction without support.
        # ----------------------------------------------------

        if has_contradiction:
            return InvestigationStatus.CONTRADICTION

        # ----------------------------------------------------
        # Nothing establishes an explanation.
        # ----------------------------------------------------

        return InvestigationStatus.INSUFFICIENT_EVIDENCE

    # ========================================================
    # CONCLUSION
    # ========================================================

    @staticmethod
    def _build_conclusion(
        *,
        status: InvestigationStatus,
        explained_amount: Decimal,
        remaining_unexplained: Decimal,
    ) -> str:
        """
        Build a deterministic human-readable conclusion.

        The conclusion describes evidence state only and does
        not claim an unsupported root cause.
        """

        if status == InvestigationStatus.RESOLVED:

            return (
                "The discrepancy is fully explained by "
                "retrieved supporting evidence. "
                f"Explained amount: {explained_amount}."
            )

        if status == InvestigationStatus.UNRESOLVED:

            return (
                "Retrieved evidence explains part of the "
                "discrepancy, but an unexplained amount "
                f"of {remaining_unexplained} remains."
            )

        if status == InvestigationStatus.CONTRADICTION:

            return (
                "Available evidence contradicts the "
                "candidate explanations and does not "
                "establish a supported explanation."
            )

        if (
            status
            == InvestigationStatus.INSUFFICIENT_EVIDENCE
        ):

            return (
                "The available evidence is insufficient "
                "to establish a supported explanation "
                "for the discrepancy."
            )

        return (
            "The investigation remains in progress."
        )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================


def investigate(
    case: InvestigationCase,
    graph: EventGraph,
) -> InvestigationResult:
    """
    Convenience function for running one investigation.
    """

    return InvestigationOrchestrator().investigate(
        case,
        graph,
    )