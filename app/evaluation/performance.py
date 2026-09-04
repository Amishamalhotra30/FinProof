from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.benchmark import generate_benchmark
from app.performance import measure_throughput


@dataclass(frozen=True)
class PerformanceMeasurement:
    cases: int
    records: int
    generation_seconds: float
    reconciliation_seconds: float

    @property
    def generation_cases_per_second(self) -> float:
        if self.generation_seconds <= 0:
            return float("inf")

        return self.cases / self.generation_seconds

    @property
    def reconciliation_cases_per_second(self) -> float:
        if self.reconciliation_seconds <= 0:
            return float("inf")

        return self.cases / self.reconciliation_seconds

    @property
    def reconciliation_records_per_second(self) -> float:
        if self.reconciliation_seconds <= 0:
            return float("inf")

        return self.records / self.reconciliation_seconds


@dataclass(frozen=True)
class PerformanceBenchmark:
    measurements: tuple[PerformanceMeasurement, ...]

    @property
    def largest_case_count(self) -> int:
        if not self.measurements:
            return 0

        return max(
            measurement.cases
            for measurement in self.measurements
        )

    @property
    def minimum_reconciliation_throughput(
        self,
    ) -> float:
        if not self.measurements:
            return 0.0

        return min(
            measurement.reconciliation_cases_per_second
            for measurement in self.measurements
        )


def measure_performance(
    case_counts: tuple[int, ...] = (
        100,
        1_000,
        5_000,
        10_000,
    ),
    seed: int = 42,
) -> PerformanceBenchmark:
    """
    Measure deterministic benchmark generation and
    reconciliation performance across increasing workloads.

    The existing reconciliation throughput utility is reused
    so Phase 8 does not duplicate production timing logic.

    Note:
        Reconciliation is the measured runtime stage here.
        This function does not claim to measure the complete
        Phase 5-7 pipeline.
    """

    measurements = []

    for index, cases in enumerate(case_counts):
        if cases <= 0:
            raise ValueError(
                "case counts must be positive"
            )

        start = perf_counter()

        benchmark = generate_benchmark(
            num_cases=cases,
            seed=seed + index,
        )

        generation_seconds = (
            perf_counter() - start
        )

        throughput = measure_throughput(
            benchmark.observed_records,
            cases=cases,
        )

        measurements.append(
            PerformanceMeasurement(
                cases=cases,
                records=throughput.records,
                generation_seconds=(
                    generation_seconds
                ),
                reconciliation_seconds=(
                    throughput.elapsed_seconds
                ),
            )
        )

    return PerformanceBenchmark(
        measurements=tuple(measurements)
    )