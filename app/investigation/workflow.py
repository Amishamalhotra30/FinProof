from app.domain.graph import EventGraph
from app.investigation.case_builder import (
    InvestigationCaseBuilder,
)
from app.investigation.investigator import (
    InvestigationOrchestrator,
)
from app.investigation.models import (
    InvestigationCase,
    InvestigationResult,
)
from app.investigation.service import (
    InvestigationService,
    InvestigationServiceResult,
)
from app.verification.models import (
    VerificationResult,
)


class InvestigationWorkflowResult:
    """
    Complete Phase 5 -> Phase 6 workflow output.

    The workflow preserves the investigation cases and their
    corresponding service results in the same deterministic
    order as the Phase 5 discrepancies.

    This class intentionally contains no financial reasoning.
    """

    def __init__(
        self,
        cases: list[InvestigationCase],
        results: list[InvestigationServiceResult],
    ):
        self.cases = tuple(cases)
        self.results = tuple(results)

    @property
    def investigation_results(
        self,
    ) -> tuple[InvestigationResult, ...]:
        """
        Convenience access to the underlying investigation
        results.
        """

        return tuple(
            item.result
            for item in self.results
        )

    @property
    def count(self) -> int:
        """
        Number of investigation cases produced.
        """

        return len(self.cases)


class InvestigationWorkflow:
    """
    Coordinates the Phase 5 -> Phase 6 investigation boundary.

    Pipeline:

        VerificationResult
            ↓
        InvestigationCaseBuilder
            ↓
        InvestigationCase[]
            ↓
        InvestigationService
            ↓
        InvestigationServiceResult[]

    Responsibilities:

        - convert Phase 5 discrepancies into cases
        - execute each Phase 6 investigation
        - preserve deterministic ordering
        - return structured investigation results

    It does not:

        - calculate financial state
        - generate hypotheses
        - retrieve evidence
        - evaluate hypotheses
        - modify VerificationResult
        - modify EventGraph
        - automatically validate investigation results
    """

    def __init__(
        self,
        case_builder: InvestigationCaseBuilder | None = None,
        investigation_service: (
            InvestigationService | None
        ) = None,
    ):
        self.case_builder = (
            case_builder
            or InvestigationCaseBuilder()
        )

        self.investigation_service = (
            investigation_service
            or InvestigationService()
        )

    def investigate(
        self,
        verification: VerificationResult,
        graph: EventGraph,
    ) -> InvestigationWorkflowResult:
        """
        Run Phase 6 investigation for every discrepancy
        produced by Phase 5.
        """

        cases = [
            self.case_builder.build(
                verification,
                discrepancy,
            )
            for discrepancy in verification.discrepancies
        ]

        results: list[
            InvestigationServiceResult
        ] = []

        for case in cases:

            result = (
                self.investigation_service.investigate(
                    case,
                    graph,
                )
            )

            results.append(result)

        return InvestigationWorkflowResult(
            cases=cases,
            results=results,
        )


def investigate_verification(
    verification: VerificationResult,
    graph: EventGraph,
) -> InvestigationWorkflowResult:
    """
    Convenience function for running the complete
    Phase 5 -> Phase 6 investigation workflow.
    """

    return InvestigationWorkflow().investigate(
        verification,
        graph,
    )