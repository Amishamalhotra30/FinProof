from dataclasses import dataclass, field
from decimal import Decimal

from app.reconstruction.result import ReconstructionResult
from app.verification.models import (
    Discrepancy,
    Materiality,
    VerificationResult,
    VerificationStatus,
)
from app.verification.verifier import (
    FinancialStateVerifier,
)


@dataclass(frozen=True)
class BatchVerificationResult:
    """
    Aggregate verification result for multiple reconstructed cases.

    This is descriptive aggregation only. It does not alter
    individual verification results or perform root-cause analysis.
    """

    results: tuple[VerificationResult, ...] = field(
        default_factory=tuple
    )

    processing_time_ms: Decimal = Decimal("0")

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def verified_cases(self) -> int:
        return sum(
            result.status
            == VerificationStatus.VERIFIED
            for result in self.results
        )

    @property
    def failed_cases(self) -> int:
        return sum(
            result.status
            == VerificationStatus.FAILED
            for result in self.results
        )

    @property
    def pending_cases(self) -> int:
        return sum(
            result.status
            == VerificationStatus.PENDING
            for result in self.results
        )

    @property
    def indeterminate_cases(self) -> int:
        return sum(
            result.status
            == VerificationStatus.INDETERMINATE
            for result in self.results
        )

    @property
    def discrepancies(self) -> list[Discrepancy]:
        discrepancies: list[Discrepancy] = []

        for result in self.results:
            discrepancies.extend(
                result.discrepancies
            )

        return discrepancies

    @property
    def total_discrepancies(self) -> int:
        return len(self.discrepancies)

    @property
    def material_discrepancies(self) -> list[Discrepancy]:
        """
        Return discrepancies classified as materially significant.

        This is descriptive aggregation only. Materiality has already
        been determined by the individual discrepancy builder.
        """

        return [
            discrepancy
            for discrepancy in self.discrepancies
            if discrepancy.materiality
            in {
                Materiality.MEDIUM,
                Materiality.HIGH,
            }
        ]

    @property
    def material_failure_count(self) -> int:
        return len(
            self.material_discrepancies
        )

    @property
    def blocking_discrepancy_count(self) -> int:
        return sum(
            discrepancy.blocking
            for discrepancy in self.discrepancies
        )

    @property
    def verification_rate(self) -> Decimal:
        if self.total_cases == 0:
            return Decimal("0")

        return (
            Decimal(self.verified_cases)
            / Decimal(self.total_cases)
        )

    @property
    def failure_rate(self) -> Decimal:
        if self.total_cases == 0:
            return Decimal("0")

        return (
            Decimal(self.failed_cases)
            / Decimal(self.total_cases)
        )

    @property
    def pending_rate(self) -> Decimal:
        if self.total_cases == 0:
            return Decimal("0")

        return (
            Decimal(self.pending_cases)
            / Decimal(self.total_cases)
        )

    @property
    def indeterminate_rate(self) -> Decimal:
        if self.total_cases == 0:
            return Decimal("0")

        return (
            Decimal(self.indeterminate_cases)
            / Decimal(self.total_cases)
        )

    @property
    def throughput(self) -> Decimal:
        """
        Cases processed per second.

        Returns zero when processing time is zero.
        """

        if self.processing_time_ms <= Decimal("0"):
            return Decimal("0")

        return (
            Decimal(self.total_cases)
            / (
                self.processing_time_ms
                / Decimal("1000")
            )
        )


class BatchFinancialStateVerifier:
    """
    Verifies multiple Phase 4 reconstruction results.

    Each reconstruction is independently verified by the same
    deterministic FinancialStateVerifier.

    No ground truth is required.
    """

    def __init__(
        self,
        verifier: FinancialStateVerifier | None = None,
    ):
        self.verifier = (
            verifier
            or FinancialStateVerifier()
        )

    def verify(
        self,
        reconstructions: list[ReconstructionResult],
    ) -> BatchVerificationResult:
        """
        Verify every supplied reconstruction independently.
        """

        started_results: list[
            VerificationResult
        ] = []

        for reconstruction in reconstructions:
            started_results.append(
                self.verifier.verify(
                    reconstruction
                )
            )

        total_processing_time = sum(
            (
                result.processing_time_ms
                or Decimal("0")
            )
            for result in started_results
        )

        return BatchVerificationResult(
            results=tuple(started_results),
            processing_time_ms=total_processing_time,
        )


def verify_batch(
    reconstructions: list[ReconstructionResult],
) -> BatchVerificationResult:
    """
    Convenience function for batch verification.
    """

    return BatchFinancialStateVerifier().verify(
        reconstructions
    )