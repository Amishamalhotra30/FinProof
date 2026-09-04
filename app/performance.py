from dataclasses import dataclass
from time import perf_counter

from app.reconciliation.controller import (
    reconcile_records,
)


@dataclass(frozen=True)
class ThroughputMetrics:
    cases: int
    records: int
    elapsed_seconds: float

    @property
    def cases_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return float("inf")

        return (
            self.cases
            / self.elapsed_seconds
        )

    @property
    def records_per_second(self) -> float:
        if self.elapsed_seconds == 0:
            return float("inf")

        return (
            self.records
            / self.elapsed_seconds
        )


def measure_throughput(
    records: dict[str, list],
    cases: int,
) -> ThroughputMetrics:

    total_records = sum(
        len(record_list)
        for record_list in records.values()
    )

    start = perf_counter()

    reconcile_records(records)

    elapsed = perf_counter() - start

    return ThroughputMetrics(
        cases=cases,
        records=total_records,
        elapsed_seconds=elapsed,
    )