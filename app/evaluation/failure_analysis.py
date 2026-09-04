from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class FailureCategory(str, Enum):
    RECONCILIATION = "RECONCILIATION"
    RECONSTRUCTION = "RECONSTRUCTION"
    VERIFICATION = "VERIFICATION"
    INVESTIGATION = "INVESTIGATION"
    DECISION = "DECISION"
    SAFETY = "SAFETY"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    PERFORMANCE = "PERFORMANCE"


class FailureType(str, Enum):
    FALSE_PASS = "FALSE_PASS"
    FALSE_FAIL = "FALSE_FAIL"
    FALSE_EXPLANATION = "FALSE_EXPLANATION"
    FALSE_RESOLUTION = "FALSE_RESOLUTION"
    FALSE_BLOCK = "FALSE_BLOCK"
    MISSED_FAILURE = "MISSED_FAILURE"
    SAFE_DEGRADATION_FAILURE = "SAFE_DEGRADATION_FAILURE"
    THROUGHPUT_REGRESSION = "THROUGHPUT_REGRESSION"
    OTHER = "OTHER"


@dataclass(frozen=True)
class FailureRecord:
    case_id: str
    category: FailureCategory
    failure_type: FailureType
    financial_value: Decimal = Decimal("0")
    description: str = ""
    corruption_type: str | None = None


@dataclass(frozen=True)
class FailureAnalysisSummary:
    total_failures: int
    total_financial_value: Decimal

    false_passes: int
    false_pass_value: Decimal

    false_fails: int
    false_fail_value: Decimal

    false_explanations: int
    false_explanation_value: Decimal

    false_resolutions: int
    false_resolution_value: Decimal

    false_blocks: int
    false_block_value: Decimal

    safe_degradation_failures: int
    safe_degradation_failure_value: Decimal

    @property
    def false_pass_value_rate(self) -> Decimal:
        return _value_rate(
            self.false_pass_value,
            self.total_financial_value,
        )

    @property
    def false_explanation_value_rate(self) -> Decimal:
        return _value_rate(
            self.false_explanation_value,
            self.total_financial_value,
        )

    @property
    def false_resolution_value_rate(self) -> Decimal:
        return _value_rate(
            self.false_resolution_value,
            self.total_financial_value,
        )

    @property
    def false_block_value_rate(self) -> Decimal:
        return _value_rate(
            self.false_block_value,
            self.total_financial_value,
        )


def _value_rate(
    value: Decimal,
    total: Decimal,
) -> Decimal:
    if total <= Decimal("0"):
        return Decimal("0")

    return (
        abs(value)
        / abs(total)
    )


class FailureAnalyzer:
    """
    Evaluation-only failure analyzer.

    It does not alter application results and does not
    participate in financial processing.
    """

    def analyze(
        self,
        failures: list[FailureRecord] | tuple[
            FailureRecord, ...
        ],
    ) -> FailureAnalysisSummary:
        total_failures = len(failures)

        total_financial_value = sum(
            (
                abs(failure.financial_value)
                for failure in failures
            ),
            Decimal("0"),
        )

        false_passes = [
            failure
            for failure in failures
            if failure.failure_type
            == FailureType.FALSE_PASS
        ]

        false_fails = [
            failure
            for failure in failures
            if failure.failure_type
            == FailureType.FALSE_FAIL
        ]

        false_explanations = [
            failure
            for failure in failures
            if failure.failure_type
            == FailureType.FALSE_EXPLANATION
        ]

        false_resolutions = [
            failure
            for failure in failures
            if failure.failure_type
            == FailureType.FALSE_RESOLUTION
        ]

        false_blocks = [
            failure
            for failure in failures
            if failure.failure_type
            == FailureType.FALSE_BLOCK
        ]

        safe_degradation_failures = [
            failure
            for failure in failures
            if failure.failure_type
            == FailureType.SAFE_DEGRADATION_FAILURE
        ]

        return FailureAnalysisSummary(
            total_failures=total_failures,
            total_financial_value=total_financial_value,

            false_passes=len(false_passes),
            false_pass_value=_sum_value(
                false_passes
            ),

            false_fails=len(false_fails),
            false_fail_value=_sum_value(
                false_fails
            ),

            false_explanations=len(
                false_explanations
            ),
            false_explanation_value=_sum_value(
                false_explanations
            ),

            false_resolutions=len(
                false_resolutions
            ),
            false_resolution_value=_sum_value(
                false_resolutions
            ),

            false_blocks=len(false_blocks),
            false_block_value=_sum_value(
                false_blocks
            ),

            safe_degradation_failures=len(
                safe_degradation_failures
            ),
            safe_degradation_failure_value=_sum_value(
                safe_degradation_failures
            ),
        )


def _sum_value(
    failures: list[FailureRecord],
) -> Decimal:
    return sum(
        (
            abs(failure.financial_value)
            for failure in failures
        ),
        Decimal("0"),
    )


def analyze_failures(
    failures: list[FailureRecord] | tuple[
        FailureRecord, ...
    ],
) -> FailureAnalysisSummary:
    return FailureAnalyzer().analyze(failures)