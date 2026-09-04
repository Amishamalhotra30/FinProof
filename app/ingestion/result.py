from dataclasses import dataclass

from app.ingestion.quality import QualityStatus


@dataclass(frozen=True)
class IngestionResult:
    record: object | None
    quality_status: QualityStatus
    errors: list[str]