from __future__ import annotations

from decimal import Decimal

from app.benchmark import generate_benchmark
from app.corruption.models import CorruptionType
from app.evaluation.ground_truth import (
    EvaluationGroundTruth,
    ExpectedCaseOutcome,
)
from app.verification.benchmark import (
    CORRUPTION_TO_CONTROLS,
    MATERIAL_CORRUPTIONS,
)


def build_benchmark_ground_truth(
    benchmark,
) -> EvaluationGroundTruth:
    """
    Convert the existing FinProof benchmark into the
    independent Phase 8 answer key.

    This function belongs exclusively to evaluation code.

    The returned ground truth must never be passed into
    production reconciliation, reconstruction, verification,
    investigation, or decision logic.
    """

    case_ids = [
        case.case_id
        for case in benchmark.ground_truth.cases
    ]

    corruption_by_case: dict[
        str,
        set[CorruptionType],
    ] = {
        case_id: set()
        for case_id in case_ids
    }

    controls_by_case: dict[
        str,
        set[str],
    ] = {
        case_id: set()
        for case_id in case_ids
    }

    material_by_case: dict[
        str,
        bool,
    ] = {
        case_id: False
        for case_id in case_ids
    }

    for event in benchmark.corruption_events:
        corruption_by_case.setdefault(
            event.case_id,
            set(),
        ).add(event.corruption_type)

        controls = CORRUPTION_TO_CONTROLS.get(
            event.corruption_type,
            frozenset(),
        )

        controls_by_case.setdefault(
            event.case_id,
            set(),
        ).update(controls)

        if event.corruption_type in MATERIAL_CORRUPTIONS:
            material_by_case[event.case_id] = True

    outcomes = []

    for case_id in case_ids:
        corruption_types = corruption_by_case.get(
            case_id,
            set(),
        )

        control_ids = controls_by_case.get(
            case_id,
            set(),
        )

        outcomes.append(
            ExpectedCaseOutcome(
                case_id=case_id,
                expected_failure=bool(
                    corruption_types
                ),
                expected_material_failure=(
                    material_by_case.get(
                        case_id,
                        False,
                    )
                ),
                expected_control_ids=frozenset(
                    control_ids
                ),
                expected_corruption_types=frozenset(
                    corruption.value
                    for corruption in corruption_types
                ),
            )
        )

    return EvaluationGroundTruth(
        cases=tuple(outcomes)
    )


def generate_evaluation_benchmark(
    num_cases: int = 100,
    seed: int = 42,
):
    """
    Generate benchmark data and its evaluation-only
    ground truth.

    The runtime pipeline should receive only:
        benchmark.observed_records

    The answer key remains in this evaluation layer.
    """

    benchmark = generate_benchmark(
        num_cases=num_cases,
        seed=seed,
    )

    ground_truth = build_benchmark_ground_truth(
        benchmark
    )

    return benchmark, ground_truth