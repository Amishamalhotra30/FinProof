from dataclasses import dataclass, field
from typing import Any

from app.ingestion.batch import BatchIngestionResult, ingest_batch
from app.ingestion.pipeline import (
    ingest_adjustment_with_quality,
    ingest_bank_statement_line_with_quality,
    ingest_fee_with_quality,
    ingest_order_with_quality,
    ingest_payment_with_quality,
    ingest_refund_with_quality,
    ingest_settlement_with_quality,
)


@dataclass(frozen=True)
class MultiSourceInput:
    orders: list[dict[str, Any]] = field(
        default_factory=list
    )
    payments: list[dict[str, Any]] = field(
        default_factory=list
    )
    refunds: list[dict[str, Any]] = field(
        default_factory=list
    )
    fees: list[dict[str, Any]] = field(
        default_factory=list
    )
    adjustments: list[dict[str, Any]] = field(
        default_factory=list
    )
    settlements: list[dict[str, Any]] = field(
        default_factory=list
    )
    bank: list[dict[str, Any]] = field(
        default_factory=list
    )


@dataclass(frozen=True)
class MultiSourceIngestionResult:
    orders: BatchIngestionResult
    payments: BatchIngestionResult
    refunds: BatchIngestionResult
    fees: BatchIngestionResult
    adjustments: BatchIngestionResult
    settlements: BatchIngestionResult
    bank: BatchIngestionResult

    @property
    def total_records(self) -> int:
        return sum(
            result.total_records
            for result in self._results()
        )

    @property
    def valid_records(self) -> list[object]:
        records: list[object] = []

        for result in self._results():
            records.extend(result.valid_records)

        return records

    @property
    def invalid_records(self) -> list[object]:
        records: list[object] = []

        for result in self._results():
            records.extend(result.invalid_records)

        return records

    @property
    def errors(self) -> list[str]:
        errors: list[str] = []

        for result in self._results():
            errors.extend(result.errors)

        return errors

    def _results(self) -> tuple[
        BatchIngestionResult,
        ...
    ]:
        return (
            self.orders,
            self.payments,
            self.refunds,
            self.fees,
            self.adjustments,
            self.settlements,
            self.bank,
        )


def ingest_sources(
    sources: MultiSourceInput,
) -> MultiSourceIngestionResult:

    return MultiSourceIngestionResult(
        orders=ingest_batch(
            sources.orders,
            ingest_order_with_quality,
            source_file="orders",
        ),
        payments=ingest_batch(
            sources.payments,
            ingest_payment_with_quality,
            source_file="payments",
        ),
        refunds=ingest_batch(
            sources.refunds,
            ingest_refund_with_quality,
            source_file="refunds",
        ),
        fees=ingest_batch(
            sources.fees,
            ingest_fee_with_quality,
            source_file="fees",
        ),
        adjustments=ingest_batch(
            sources.adjustments,
            ingest_adjustment_with_quality,
            source_file="adjustments",
        ),
        settlements=ingest_batch(
            sources.settlements,
            ingest_settlement_with_quality,
            source_file="settlements",
        ),
        bank=ingest_batch(
            sources.bank,
            ingest_bank_statement_line_with_quality,
            source_file="bank",
        ),
    )