from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ExpectedCaseOutcome:
    """
    Evaluation-only expected outcome for one benchmark case.

    This object must never enter the runtime application pipeline.
    """

    case_id: str

    expected_failure: bool
    expected_material_failure: bool = False

    expected_decision: str | None = None

    financial_impact: Decimal = Decimal("0")

    expected_control_ids: frozenset[str] = frozenset()

    expected_corruption_types: frozenset[str] = frozenset()


@dataclass(frozen=True)
class EvaluationGroundTruth:
    """
    Hidden evaluation answer key.

    The runtime application must never consume this object.
    """

    cases: tuple[ExpectedCaseOutcome, ...]

    def by_case_id(
        self,
    ) -> dict[str, ExpectedCaseOutcome]:
        return {
            case.case_id: case
            for case in self.cases
        }

    def get(
        self,
        case_id: str,
    ) -> ExpectedCaseOutcome | None:
        return self.by_case_id().get(case_id)


def build_ground_truth(
    cases,
    expected_failure_case_ids: set[str] | None = None,
    expected_material_failure_case_ids: set[str] | None = None,
    expected_decisions: dict[str, str] | None = None,
    financial_impacts: dict[str, Decimal] | None = None,
) -> EvaluationGroundTruth:
    """
    Generic evaluation answer-key constructor.

    Retained for unit tests and smaller evaluation datasets.
    """

    failure_ids = (
        expected_failure_case_ids
        if expected_failure_case_ids is not None
        else set()
    )

    material_ids = (
        expected_material_failure_case_ids
        if expected_material_failure_case_ids is not None
        else set()
    )

    decisions = (
        expected_decisions
        if expected_decisions is not None
        else {}
    )

    impacts = (
        financial_impacts
        if financial_impacts is not None
        else {}
    )

    outcomes = []

    for case in cases:
        case_id = case.case_id

        outcomes.append(
            ExpectedCaseOutcome(
                case_id=case_id,
                expected_failure=(
                    case_id in failure_ids
                ),
                expected_material_failure=(
                    case_id in material_ids
                ),
                expected_decision=(
                    decisions.get(case_id)
                ),
                financial_impact=(
                    impacts.get(
                        case_id,
                        Decimal("0"),
                    )
                ),
            )
        )

    return EvaluationGroundTruth(
        cases=tuple(outcomes)
    )