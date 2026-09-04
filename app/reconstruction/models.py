from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field

from app.domain.enums import EventType


class TimestampType(str, Enum):
    """
    Describes the semantic meaning of an event timestamp.

    Different source timestamps must not be treated as interchangeable.
    """

    CREATED_AT = "CREATED_AT"
    CAPTURED_AT = "CAPTURED_AT"
    PROCESSED_AT = "PROCESSED_AT"
    SETTLED_AT = "SETTLED_AT"
    VALUE_DATE = "VALUE_DATE"
    EVENT_TIME = "EVENT_TIME"


class ReconstructionStatus(str, Enum):
    """
    Describes the state of the reconstruction itself.

    This is not a financial correctness judgment.
    """

    RECONSTRUCTED = "RECONSTRUCTED"
    PARTIALLY_RECONSTRUCTED = "PARTIALLY_RECONSTRUCTED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRECONSTRUCTABLE = "UNRECONSTRUCTABLE"


class ReconstructedEvent(BaseModel):
    """
    A financial event reconstructed from observed canonical evidence.

    The event represents what the available evidence describes.
    It does not infer missing events or financial correctness.
    """

    event_id: str

    event_type: EventType

    timestamp: datetime

    timestamp_type: TimestampType

    amount: Decimal | None = None

    currency: str = "INR"

    source_evidence_ids: list[str] = Field(
        default_factory=list
    )

    relationship_ids: list[str] = Field(
        default_factory=list
    )

    parent_event_ids: list[str] = Field(
        default_factory=list
    )

    child_event_ids: list[str] = Field(
        default_factory=list
    )

    attributes: dict[str, str] = Field(
        default_factory=dict
    )


class ObservedFinancialState(BaseModel):
    """
    Financial state calculated only from observed reconstructed events.

    No expected values or ground-truth values belong here.
    """

    gross_captured: Decimal = Decimal("0")

    total_refunded: Decimal = Decimal("0")

    total_fees: Decimal = Decimal("0")

    total_tax: Decimal = Decimal("0")

    total_adjustments: Decimal = Decimal("0")

    total_settled: Decimal = Decimal("0")

    total_bank_credited: Decimal = Decimal("0")

    event_counts: dict[str, int] = Field(
        default_factory=dict
    )


class ReconstructionResult(BaseModel):
    """
    Complete Phase 4 reconstruction output for a case.

    This contains the observed event sequence and observed
    financial state without making a correctness judgment.
    """

    case_id: str

    status: ReconstructionStatus

    events: list[ReconstructedEvent] = Field(
        default_factory=list
    )

    state: ObservedFinancialState = Field(
        default_factory=ObservedFinancialState
    )

    relationship_ids: list[str] = Field(
        default_factory=list
    )