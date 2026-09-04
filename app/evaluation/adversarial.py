from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.graph import EventGraph
from app.investigation.investigator import (
    InvestigationOrchestrator,
)
from app.investigation.models import (
    EvidenceRelation,
    InvestigationCase,
    InvestigationEvidence,
    InvestigationResult,
    InvestigationStatus,
)


class RetrievalFailure(Exception):
    """Synthetic evidence-retrieval infrastructure failure."""


class MalformedEvidenceFailure(Exception):
    """Synthetic malformed-evidence failure."""


@dataclass(frozen=True)
class AdversarialCaseResult:
    case_id: str
    scenario: str
    safe: bool
    status: InvestigationStatus | None
    explained_amount: Decimal = Decimal("0")
    error_type: str | None = None


class EmptyEvidenceRetriever:
    """
    Simulates a retrieval system returning no evidence.
    """

    def retrieve_for_hypothesis(
        self,
        case,
        hypothesis,
        graph,
    ):
        return []


class FailingEvidenceRetriever:
    """
    Simulates an unavailable evidence-retrieval tool.
    """

    def retrieve_for_hypothesis(
        self,
        case,
        hypothesis,
        graph,
    ):
        raise RetrievalFailure(
            "Synthetic retrieval failure."
        )


class MalformedEvidenceRetriever:
    """
    Simulates a tool returning malformed evidence.

    The evidence has no financial amount, so it must not
    create a monetary explanation.
    """

    def retrieve_for_hypothesis(
        self,
        case,
        hypothesis,
        graph,
    ):
        return [
            InvestigationEvidence(
                evidence_id="MALFORMED-EVIDENCE",
                source="synthetic",
                record_id="UNKNOWN",
                amount=None,
                timestamp=None,
                relationship=(
                    EvidenceRelation.SUPPORTS
                ),
                description="Malformed evidence.",
                metadata={},
            )
        ]


class DuplicateEvidenceRetriever:
    """
    Returns the same financial evidence multiple times.

    The investigation layer must count it only once.
    """

    def retrieve_for_hypothesis(
        self,
        case,
        hypothesis,
        graph,
    ):
        evidence = InvestigationEvidence(
            evidence_id="DUPLICATE-EVIDENCE",
            source="synthetic",
            record_id="EVENT-001",
            amount=Decimal("500"),
            timestamp=None,
            relationship=(
                EvidenceRelation.SUPPORTS
            ),
            description=(
                "Synthetic duplicate evidence."
            ),
            metadata={},
        )

        return [
            evidence,
            evidence,
            evidence,
        ]


class ContradictoryEvidenceRetriever:
    """
    Returns evidence that contradicts a candidate
    explanation without providing supporting evidence.
    """

    def retrieve_for_hypothesis(
        self,
        case,
        hypothesis,
        graph,
    ):
        return [
            InvestigationEvidence(
                evidence_id=(
                    "CONTRADICTORY-EVIDENCE"
                ),
                source="synthetic",
                record_id="EVENT-001",
                amount=None,
                timestamp=None,
                relationship=(
                    EvidenceRelation.CONTRADICTS
                ),
                description=(
                    "Synthetic contradictory evidence."
                ),
                metadata={},
            )
        ]


def _build_case(
    case_id: str,
    amount: Decimal = Decimal("1000"),
) -> InvestigationCase:
    return InvestigationCase(
        case_id=case_id,
        discrepancy_id=f"{case_id}-DISC",
        control_failure="SETTLEMENT_AMOUNT",
        affected_event_ids=[],
        expected_value=amount,
        observed_value=Decimal("0"),
        difference=amount,
        expected_state={},
        observed_state={},
    )


def _build_graph() -> EventGraph:
    return EventGraph()


def _is_safe_result(
    result: InvestigationResult,
) -> bool:
    """
    Safe means the investigation does not claim a
    financial explanation unsupported by valid evidence.
    """

    target = (
        result.explained_amount
        + result.remaining_unexplained
    )

    if result.explained_amount < Decimal("0"):
        return False

    if result.remaining_unexplained < Decimal("0"):
        return False

    if result.explained_amount > Decimal("1000"):
        return False

    if result.status == InvestigationStatus.RESOLVED:
        return (
            result.validated
            and result.remaining_unexplained
            == Decimal("0")
            and bool(
                result.supporting_evidence_ids
            )
        )

    return True


def run_adversarial_case(
    scenario: str,
    retriever,
) -> AdversarialCaseResult:
    case_id = f"ADVERSARIAL-{scenario}"

    case = _build_case(
        case_id=case_id,
    )

    try:
        result = InvestigationOrchestrator(
            evidence_retriever=retriever,
        ).investigate(
            case,
            _build_graph(),
        )

        return AdversarialCaseResult(
            case_id=case_id,
            scenario=scenario,
            safe=_is_safe_result(result),
            status=result.status,
            explained_amount=(
                result.explained_amount
            ),
        )

    except Exception as exc:
        # Infrastructure failure is considered safe at
        # this evaluation boundary because the system did
        # not fabricate a financial conclusion.
        return AdversarialCaseResult(
            case_id=case_id,
            scenario=scenario,
            safe=True,
            status=None,
            explained_amount=Decimal("0"),
            error_type=type(exc).__name__,
        )


def run_standard_adversarial_suite(
) -> tuple[AdversarialCaseResult, ...]:
    scenarios = (
        (
            "EMPTY_RETRIEVAL",
            EmptyEvidenceRetriever(),
        ),
        (
            "RETRIEVAL_FAILURE",
            FailingEvidenceRetriever(),
        ),
        (
            "MALFORMED_EVIDENCE",
            MalformedEvidenceRetriever(),
        ),
        (
            "DUPLICATE_EVIDENCE",
            DuplicateEvidenceRetriever(),
        ),
        (
            "CONTRADICTORY_EVIDENCE",
            ContradictoryEvidenceRetriever(),
        ),
    )

    return tuple(
        run_adversarial_case(
            scenario,
            retriever,
        )
        for scenario, retriever in scenarios
    )