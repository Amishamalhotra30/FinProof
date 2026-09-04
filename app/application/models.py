from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class BatchStatus(str, Enum):
    CREATED = "CREATED"
    INGESTING = "INGESTING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class BatchMetadata:
    batch_id: str
    name: str
    scenario: str
    seed: int
    status: BatchStatus = BatchStatus.CREATED


@dataclass
class PipelineStage:
    name: str
    status: str = "PENDING"
    duration_ms: float = 0.0
    records_processed: int = 0
    error: str | None = None


@dataclass
class BatchRuntime:
    """
    In-memory runtime state for one Phase 9 batch.

    This class stores references to outputs produced by the existing
    FinProof phases. It does not implement financial-control logic.
    """

    metadata: BatchMetadata

    stages: list[PipelineStage] = field(default_factory=list)

    source_records: dict[str, Any] = field(default_factory=dict)

    evidence_graph: Any | None = None
    reconciliation_result: Any | None = None
    reconstruction_result: Any | None = None
    verification_result: Any | None = None
    investigation_result: Any | None = None

    decisions: dict[str, Any] = field(default_factory=dict)

    created_at: str | None = None
    completed_at: str | None = None

    def stage(self, name: str) -> PipelineStage:
        for stage in self.stages:
            if stage.name == name:
                return stage

        stage = PipelineStage(name=name)
        self.stages.append(stage)
        return stage

    @property
    def case_count(self) -> int:
        if self.verification_result is None:
            return 0

        return len(
            getattr(
                self.verification_result,
                "discrepancies",
                (),
            )
        )

    @property
    def financial_impact(self) -> Decimal:
        if self.verification_result is None:
            return Decimal("0")

        total = Decimal("0")

        for discrepancy in getattr(
            self.verification_result,
            "discrepancies",
            (),
        ):
            total += abs(
                Decimal(str(discrepancy.difference))
            )

        return total