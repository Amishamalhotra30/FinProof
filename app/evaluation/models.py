from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class EvaluationSplit(str, Enum):
    SMOKE = "SMOKE"
    STANDARD = "STANDARD"
    STRESS = "STRESS"
    HELD_OUT = "HELD_OUT"


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    split: EvaluationSplit
    seed: int


@dataclass(frozen=True)
class CaseEvaluation:
    case_id: str

    expected_failure: bool
    detected_failure: bool

    expected_material_failure: bool = False
    detected_material_failure: bool = False

    expected_decision: str | None = None
    actual_decision: str | None = None

    financial_impact: Decimal = Decimal("0")

    @property
    def failure_correct(self) -> bool:
        return (
            self.expected_failure
            == self.detected_failure
        )

    @property
    def decision_correct(self) -> bool:
        if (
            self.expected_decision is None
            or self.actual_decision is None
        ):
            return True

        return (
            self.expected_decision
            == self.actual_decision
        )


@dataclass(frozen=True)
class EvaluationSummary:
    split: EvaluationSplit
    total_cases: int

    evaluated_cases: int
    skipped_cases: int

    expected_failures: int
    detected_failures: int

    false_passes: int
    false_fails: int

    decision_matches: int
    decision_mismatches: int

    total_financial_impact: Decimal = Decimal("0")
    processing_time_ms: Decimal = Decimal("0")

    @property
    def false_pass_rate(self) -> Decimal:
        if self.expected_failures == 0:
            return Decimal("0")

        return (
            Decimal(self.false_passes)
            / Decimal(self.expected_failures)
        )

    @property
    def false_fail_rate(self) -> Decimal:
        actual_passes = (
            self.total_cases
            - self.expected_failures
        )

        if actual_passes <= 0:
            return Decimal("0")

        return (
            Decimal(self.false_fails)
            / Decimal(actual_passes)
        )

    @property
    def decision_accuracy(self) -> Decimal:
        if self.evaluated_cases == 0:
            return Decimal("0")

        return (
            Decimal(self.decision_matches)
            / Decimal(self.evaluated_cases)
        )

    @property
    def throughput(self) -> Decimal:
        if self.processing_time_ms <= Decimal("0"):
            return Decimal("0")

        return (
            Decimal(self.evaluated_cases)
            / (
                self.processing_time_ms
                / Decimal("1000")
            )
        )