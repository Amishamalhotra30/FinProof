from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ControlEvaluation:
    """
    Evaluation metrics for one verification control.

    These metrics compare verifier output against known
    ground-truth outcomes. They are evaluation-only and are
    never used by the runtime verifier.
    """

    control_id: str

    true_positives: int = 0
    true_negatives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def total(self) -> int:
        return (
            self.true_positives
            + self.true_negatives
            + self.false_positives
            + self.false_negatives
        )

    @property
    def precision(self) -> Decimal:
        denominator = (
            self.true_positives
            + self.false_positives
        )

        if denominator == 0:
            return Decimal("0")

        return (
            Decimal(self.true_positives)
            / Decimal(denominator)
        )

    @property
    def recall(self) -> Decimal:
        denominator = (
            self.true_positives
            + self.false_negatives
        )

        if denominator == 0:
            return Decimal("0")

        return (
            Decimal(self.true_positives)
            / Decimal(denominator)
        )

    @property
    def false_pass_rate(self) -> Decimal:
        """
        Percentage of actual failures incorrectly passed.
        """

        denominator = (
            self.true_positives
            + self.false_negatives
        )

        if denominator == 0:
            return Decimal("0")

        return (
            Decimal(self.false_negatives)
            / Decimal(denominator)
        )

    @property
    def false_fail_rate(self) -> Decimal:
        """
        Percentage of actual passes incorrectly failed.
        """

        denominator = (
            self.true_negatives
            + self.false_positives
        )

        if denominator == 0:
            return Decimal("0")

        return (
            Decimal(self.false_positives)
            / Decimal(denominator)
        )


@dataclass(frozen=True)
class VerificationEvaluation:
    """
    Batch-level evaluation of Phase 5 verification.

    This object belongs exclusively to the evaluation layer.
    It may use ground truth and must never be consumed by the
    runtime verification engine.
    """

    controls: tuple[ControlEvaluation, ...] = ()

    total_cases: int = 0

    actual_failures: int = 0
    detected_failures: int = 0

    actual_material_failures: int = 0
    detected_material_failures: int = 0

    actual_discrepancies: int = 0
    detected_discrepancies: int = 0

    pending_expected: int = 0
    pending_correct: int = 0

    processing_time_ms: Decimal = Decimal("0")

    @property
    def control_precision(self) -> Decimal:
        if not self.controls:
            return Decimal("0")

        values = [
            control.precision
            for control in self.controls
        ]

        return sum(values, Decimal("0")) / Decimal(
            len(values)
        )

    @property
    def control_recall(self) -> Decimal:
        if not self.controls:
            return Decimal("0")

        values = [
            control.recall
            for control in self.controls
        ]

        return sum(values, Decimal("0")) / Decimal(
            len(values)
        )

    @property
    def false_pass_rate(self) -> Decimal:
        if self.actual_failures == 0:
            return Decimal("0")

        return (
            Decimal(
                self.actual_failures
                - self.detected_failures
            )
            / Decimal(self.actual_failures)
        )

    @property
    def false_fail_rate(self) -> Decimal:
        if self.total_cases == 0:
            return Decimal("0")

        actual_passes = (
            self.total_cases
            - self.actual_failures
        )

        if actual_passes <= 0:
            return Decimal("0")

        false_failures = (
            actual_passes
            - (
                self.total_cases
                - self.detected_failures
            )
        )

        if false_failures < 0:
            false_failures = 0

        return (
            Decimal(false_failures)
            / Decimal(actual_passes)
        )

    @property
    def pending_classification_accuracy(
        self,
    ) -> Decimal:
        if self.pending_expected == 0:
            return Decimal("0")

        return (
            Decimal(self.pending_correct)
            / Decimal(self.pending_expected)
        )

    @property
    def material_failure_detection_rate(
        self,
    ) -> Decimal:
        if self.actual_material_failures == 0:
            return Decimal("0")

        return (
            Decimal(
                self.detected_material_failures
            )
            / Decimal(
                self.actual_material_failures
            )
        )

    @property
    def financial_discrepancy_coverage(
        self,
    ) -> Decimal:
        if self.actual_discrepancies == 0:
            return Decimal("0")

        return (
            Decimal(
                self.detected_discrepancies
            )
            / Decimal(
                self.actual_discrepancies
            )
        )

    @property
    def verification_throughput(
        self,
    ) -> Decimal:
        if self.processing_time_ms <= Decimal("0"):
            return Decimal("0")

        return (
            Decimal(self.total_cases)
            / (
                self.processing_time_ms
                / Decimal("1000")
            )
        )