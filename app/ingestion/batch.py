from dataclasses import dataclass
from typing import Any, Callable

from app.ingestion.quality import QualityStatus
from app.ingestion.result import IngestionResult


@dataclass(frozen=True)
class BatchIngestionResult:
    valid_records: list[object]
    invalid_records: list[object]
    errors: list[str]

    @property
    def total_records(self) -> int:
        return (
            len(self.valid_records)
            + len(self.invalid_records)
        )

    @property
    def valid_count(self) -> int:
        return len(self.valid_records)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_records)


def ingest_batch(
    rows: list[dict[str, Any]],
    ingest_function: Callable,
    source_file: str,
    start_row: int = 1,
) -> BatchIngestionResult:

    valid_records: list[object] = []
    invalid_records: list[object] = []
    errors: list[str] = []

    for offset, row in enumerate(rows):

        source_row = start_row + offset

        try:
            result: IngestionResult = (
                ingest_function(
                    row,
                    source_file,
                    source_row,
                )
            )

        except Exception as exc:
            errors.append(
                f"{source_file}:{source_row}: "
                f"{type(exc).__name__}: {exc}"
            )
            continue

        if result.quality_status == QualityStatus.VALID:
            if result.record is not None:
                valid_records.append(
                    result.record
                )

        else:
            invalid_records.append(
                row
            )

            for error in result.errors:
                errors.append(
                    f"{source_file}:{source_row}: "
                    f"{error}"
                )

    return BatchIngestionResult(
        valid_records=valid_records,
        invalid_records=invalid_records,
        errors=errors,
    )