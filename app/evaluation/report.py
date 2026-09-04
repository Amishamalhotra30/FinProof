from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Phase8Report:
    """
    Consolidated Phase 8 evaluation report.

    This is evaluation-only. It does not participate in
    the production financial-control pipeline.
    """

    benchmark_cases: int

    verification_cases: int
    investigation_cases: int
    decision_cases: int

    verification_false_pass_rate: Decimal
    verification_false_fail_rate: Decimal
    verification_material_detection_rate: Decimal
    verification_discrepancy_coverage: Decimal

    investigation_coverage: Decimal
    investigation_full_explanation_rate: Decimal
    investigation_false_explanation_rate: Decimal
    investigation_explanation_coverage: Decimal

    decision_automation_rate: Decimal
    decision_human_review_rate: Decimal
    decision_false_resolution_rate: Decimal

    verification_processing_time_ms: Decimal
    investigation_processing_time_ms: Decimal
    decision_processing_time_ms: Decimal

    verification_throughput: Decimal
    investigation_throughput: Decimal
    decision_throughput: Decimal

    @property
    def safety_status(self) -> str:
        """
        Conservative aggregate safety classification.

        Any non-zero false-pass, false-explanation, or
        false-resolution rate causes REVIEW_REQUIRED.
        """

        if (
            self.verification_false_pass_rate > Decimal("0")
            or self.investigation_false_explanation_rate
            > Decimal("0")
            or self.decision_false_resolution_rate
            > Decimal("0")
        ):
            return "REVIEW_REQUIRED"

        return "SAFE"

    @property
    def overall_status(self) -> str:
        if self.safety_status != "SAFE":
            return "REVIEW_REQUIRED"

        return "EVALUATED"