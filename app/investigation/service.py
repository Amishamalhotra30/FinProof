from dataclasses import dataclass

from app.domain.graph import EventGraph
from app.investigation.investigator import (
    InvestigationOrchestrator,
)
from app.investigation.models import (
    InvestigationCase,
    InvestigationResult,
)


@dataclass(frozen=True)
class InvestigationServiceResult:
    """
    Complete Phase 6 investigation service output.

    The service result wraps the investigation result while
    keeping the orchestration boundary explicit.

    No financial facts are calculated here.
    """

    result: InvestigationResult

    @property
    def investigation_id(self) -> str:
        return self.result.investigation_id

    @property
    def case_id(self) -> str:
        return self.result.case_id

    @property
    def discrepancy_id(self) -> str:
        return self.result.discrepancy_id

    @property
    def status(self):
        return self.result.status

    @property
    def hypotheses(self):
        return self.result.hypotheses

    @property
    def explained_amount(self):
        return self.result.explained_amount

    @property
    def remaining_unexplained(self):
        return self.result.remaining_unexplained

    @property
    def supporting_evidence_ids(self):
        return self.result.supporting_evidence_ids

    @property
    def conclusion(self):
        return self.result.conclusion

    @property
    def validated(self) -> bool:
        return self.result.validated


class InvestigationService:
    """
    Public orchestration boundary for Phase 6.

    Responsibilities:

        1. Accept a prepared InvestigationCase.
        2. Execute the Phase 6 investigation workflow.
        3. Return a stable service-level result.

    It does not:

        - build the investigation case
        - generate hypotheses itself
        - retrieve evidence itself
        - evaluate hypotheses itself
        - invent evidence
        - determine financial correctness
        - automatically validate the result
        - modify the EventGraph
        - repair financial records
        - use an LLM directly

    Those responsibilities belong to the underlying Phase 6
    components.
    """

    def __init__(
        self,
        orchestrator: InvestigationOrchestrator | None = None,
    ):
        self.orchestrator = (
            orchestrator
            or InvestigationOrchestrator()
        )

    def investigate(
        self,
        case: InvestigationCase,
        graph: EventGraph,
    ) -> InvestigationServiceResult:
        """
        Execute one Phase 6 investigation.

        Validation is intentionally not performed here.
        The underlying InvestigationResult therefore retains
        validated=False unless a separate validation step has
        been explicitly performed.
        """

        result = self.orchestrator.investigate(
            case,
            graph,
        )

        return InvestigationServiceResult(
            result=result,
        )


def investigate_case(
    case: InvestigationCase,
    graph: EventGraph,
) -> InvestigationServiceResult:
    """
    Convenience function for investigating one case.
    """

    return InvestigationService().investigate(
        case,
        graph,
    )