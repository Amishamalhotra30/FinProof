from __future__ import annotations

from dataclasses import dataclass

from app.evaluation.models import (
    EvaluationCase,
    EvaluationSplit,
)


@dataclass(frozen=True)
class EvaluationDataset:
    """
    Deterministic Phase 8 evaluation dataset.

    Dataset construction is independent from the runtime
    decision-making pipeline.
    """

    cases: tuple[EvaluationCase, ...]

    @property
    def total_cases(self) -> int:
        return len(self.cases)

    def cases_for_split(
        self,
        split: EvaluationSplit,
    ) -> tuple[EvaluationCase, ...]:
        return tuple(
            case
            for case in self.cases
            if case.split == split
        )


def build_dataset(
    smoke_cases: int = 10,
    standard_cases: int = 100,
    stress_cases: int = 1000,
    held_out_cases: int = 100,
    seed: int = 42,
) -> EvaluationDataset:
    """
    Build a deterministic Phase 8 dataset.

    Each split receives a deterministic seed derived from
    the supplied master seed.
    """

    if smoke_cases < 0:
        raise ValueError("smoke_cases cannot be negative")

    if standard_cases < 0:
        raise ValueError("standard_cases cannot be negative")

    if stress_cases < 0:
        raise ValueError("stress_cases cannot be negative")

    if held_out_cases < 0:
        raise ValueError("held_out_cases cannot be negative")

    cases: list[EvaluationCase] = []

    split_config = (
        (
            EvaluationSplit.SMOKE,
            smoke_cases,
            seed,
        ),
        (
            EvaluationSplit.STANDARD,
            standard_cases,
            seed + 1_000,
        ),
        (
            EvaluationSplit.STRESS,
            stress_cases,
            seed + 2_000,
        ),
        (
            EvaluationSplit.HELD_OUT,
            held_out_cases,
            seed + 3_000,
        ),
    )

    case_number = 1

    for split, count, split_seed in split_config:
        for offset in range(count):
            cases.append(
                EvaluationCase(
                    case_id=f"EVAL_{case_number:06d}",
                    split=split,
                    seed=split_seed + offset,
                )
            )

            case_number += 1

    return EvaluationDataset(
        cases=tuple(cases)
    )