from dataclasses import dataclass
from decimal import Decimal

from app.investigation.models import (
    HypothesisFinding,
    HypothesisStatus,
    InvestigationResult,
    InvestigationStatus,
)


@dataclass(frozen=True)
class InvestigationReport:
    """
    Human- and machine-readable representation of one
    completed Phase 6 investigation.

    This object is a presentation boundary over an existing
    InvestigationResult.

    It does not:
        - calculate financial explanations
        - change investigation status
        - evaluate hypotheses
        - retrieve evidence
        - validate the investigation
        - infer root causes
        - modify the underlying InvestigationResult
    """

    investigation_id: str
    case_id: str
    discrepancy_id: str

    status: InvestigationStatus

    control_failure: str | None

    expected_value: Decimal | None
    observed_value: Decimal | None
    difference: Decimal | None

    explained_amount: Decimal
    remaining_unexplained: Decimal

    hypotheses: tuple[HypothesisFinding, ...]

    supporting_evidence_ids: tuple[str, ...]

    conclusion: str | None

    validated: bool

    @property
    def resolved(self) -> bool:
        """
        Whether the investigation reached RESOLVED status.
        """

        return (
            self.status
            == InvestigationStatus.RESOLVED
        )

    @property
    def has_unexplained_amount(self) -> bool:
        """
        Whether any discrepancy amount remains unexplained.
        """

        return (
            self.remaining_unexplained
            > Decimal("0")
        )

    @property
    def supported_hypotheses(
        self,
    ) -> tuple[HypothesisFinding, ...]:
        """
        Hypotheses with explicit supporting evidence.
        """

        return tuple(
            finding
            for finding in self.hypotheses
            if finding.status
            in {
                HypothesisStatus.SUPPORTED,
                HypothesisStatus.WEAKLY_SUPPORTED,
            }
        )

    @property
    def contradicted_hypotheses(
        self,
    ) -> tuple[HypothesisFinding, ...]:
        """
        Hypotheses explicitly contradicted by evidence.
        """

        return tuple(
            finding
            for finding in self.hypotheses
            if finding.status
            == HypothesisStatus.CONTRADICTED
        )

    @property
    def unresolved_hypotheses(
        self,
    ) -> tuple[HypothesisFinding, ...]:
        """
        Hypotheses for which no decisive explanation exists.
        """

        return tuple(
            finding
            for finding in self.hypotheses
            if finding.status
            in {
                HypothesisStatus.UNDETERMINED,
                HypothesisStatus.UNSUPPORTED,
            }
        )

    @property
    def hypothesis_count(self) -> int:
        """
        Number of candidate hypotheses evaluated.
        """

        return len(self.hypotheses)

    @property
    def supporting_evidence_count(self) -> int:
        """
        Number of unique supporting evidence IDs exposed by
        the investigation result.
        """

        return len(
            self.supporting_evidence_ids
        )

    def to_dict(self) -> dict:
        """
        Convert the report into a JSON-friendly dictionary.

        Decimal values are deliberately preserved as Decimal
        objects here so callers can choose their own serialization
        policy without losing financial precision.
        """

        return {
            "investigation_id": (
                self.investigation_id
            ),
            "case_id": self.case_id,
            "discrepancy_id": (
                self.discrepancy_id
            ),
            "status": self.status.value,
            "control_failure": (
                self.control_failure
            ),
            "expected_value": (
                self.expected_value
            ),
            "observed_value": (
                self.observed_value
            ),
            "difference": self.difference,
            "explained_amount": (
                self.explained_amount
            ),
            "remaining_unexplained": (
                self.remaining_unexplained
            ),
            "hypotheses": [
                {
                    "hypothesis_type": (
                        finding.hypothesis_type.value
                    ),
                    "status": (
                        finding.status.value
                    ),
                    "explained_amount": (
                        finding.explained_amount
                    ),
                    "evidence_ids": list(
                        finding.evidence_ids
                    ),
                    "contradicting_evidence_ids": list(
                        finding.contradicting_evidence_ids
                    ),
                    "reasoning": (
                        finding.reasoning
                    ),
                }
                for finding in self.hypotheses
            ],
            "supporting_evidence_ids": list(
                self.supporting_evidence_ids
            ),
            "conclusion": self.conclusion,
            "validated": self.validated,
        }


class InvestigationReportBuilder:
    """
    Builds an InvestigationReport from an existing
    InvestigationResult.

    The builder is intentionally read-only.

    It does not perform investigation logic. All financial
    values, hypothesis statuses, evidence IDs, and conclusions
    are copied from the supplied result.
    """

    def build(
        self,
        result: InvestigationResult,
        *,
        control_failure: str | None = None,
        expected_value: Decimal | None = None,
        observed_value: Decimal | None = None,
        difference: Decimal | None = None,
    ) -> InvestigationReport:
        """
        Build a report from one InvestigationResult.

        Optional discrepancy metadata may be supplied by the
        caller when available from the InvestigationCase.

        No values are inferred when they are not supplied.
        """

        return InvestigationReport(
            investigation_id=(
                result.investigation_id
            ),
            case_id=result.case_id,
            discrepancy_id=(
                result.discrepancy_id
            ),
            status=result.status,
            control_failure=control_failure,
            expected_value=expected_value,
            observed_value=observed_value,
            difference=difference,
            explained_amount=(
                result.explained_amount
            ),
            remaining_unexplained=(
                result.remaining_unexplained
            ),
            hypotheses=tuple(
                result.hypotheses
            ),
            supporting_evidence_ids=tuple(
                result.supporting_evidence_ids
            ),
            conclusion=result.conclusion,
            validated=result.validated,
        )


def build_investigation_report(
    result: InvestigationResult,
    *,
    control_failure: str | None = None,
    expected_value: Decimal | None = None,
    observed_value: Decimal | None = None,
    difference: Decimal | None = None,
) -> InvestigationReport:
    """
    Convenience function for building one investigation report.
    """

    return InvestigationReportBuilder().build(
        result,
        control_failure=control_failure,
        expected_value=expected_value,
        observed_value=observed_value,
        difference=difference,
    )