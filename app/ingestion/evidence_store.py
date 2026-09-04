from collections import defaultdict
from typing import Any

from app.ingestion.coordinator import (
    MultiSourceIngestionResult,
)


class EvidenceStore:

    def __init__(
        self,
        result: MultiSourceIngestionResult,
    ):
        self._records: dict[str, object] = {}
        self._by_source: dict[str, list[object]] = (
            defaultdict(list)
        )
        self._by_reference: dict[str, list[object]] = (
            defaultdict(list)
        )

        self._index(result)

    def _index(
        self,
        result: MultiSourceIngestionResult,
    ) -> None:

        for record in result.valid_records:

            evidence_id = record.evidence_id

            self._records[evidence_id] = record

            self._by_source[
                record.source_type
            ].append(record)

            if (
                record.normalized_reference
                is not None
            ):
                self._by_reference[
                    record.normalized_reference
                ].append(record)

    def get(
        self,
        evidence_id: str,
    ) -> object | None:

        return self._records.get(evidence_id)

    def by_source_type(
        self,
        source_type: str,
    ) -> list[object]:

        return list(
            self._by_source.get(
                source_type,
                [],
            )
        )

    def by_reference(
        self,
        reference: str,
    ) -> list[object]:

        return list(
            self._by_reference.get(
                reference.strip().upper(),
                [],
            )
        )

    @property
    def count(self) -> int:
        return len(self._records)