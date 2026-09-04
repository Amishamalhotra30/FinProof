from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.enums import EventType, RecordSource


class FinancialEvent(BaseModel):
    event_id: str
    event_type: EventType
    entity_id: str

    amount: Decimal | None = None
    currency: str = "INR"

    timestamp: datetime

    related_event_ids: list[str] = Field(default_factory=list)

    source: RecordSource

    metadata: dict[str, str] = Field(default_factory=dict)