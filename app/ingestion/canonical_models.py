from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.ingestion.quality import QualityStatus


class Provenance(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int


class CanonicalOrder(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int

    order_id: str
    customer_id: str
    amount: Decimal
    currency: str
    event_timestamp: datetime
    status: str

    raw_reference: str | None = None
    normalized_reference: str | None = None

    raw_record: dict = Field(default_factory=dict)

    quality_status: QualityStatus = QualityStatus.VALID


class CanonicalPayment(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int

    payment_id: str
    order_id: str
    amount: Decimal
    currency: str
    event_timestamp: datetime
    status: str

    raw_reference: str | None = None
    normalized_reference: str | None = None

    raw_record: dict = Field(default_factory=dict)

    quality_status: QualityStatus = QualityStatus.VALID


class CanonicalRefund(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int

    refund_id: str
    payment_id: str
    amount: Decimal
    event_timestamp: datetime
    status: str

    raw_reference: str | None = None
    normalized_reference: str | None = None

    raw_record: dict = Field(default_factory=dict)

    quality_status: QualityStatus = QualityStatus.VALID


class CanonicalFee(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int

    fee_id: str
    payment_id: str
    amount: Decimal
    event_timestamp: datetime
    status: str

    raw_reference: str | None = None
    normalized_reference: str | None = None

    raw_record: dict = Field(default_factory=dict)

    quality_status: QualityStatus = QualityStatus.VALID


class CanonicalAdjustment(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int

    event_id: str
    payment_id: str
    event_type: str
    amount: Decimal
    event_timestamp: datetime
    status: str

    raw_reference: str | None = None
    normalized_reference: str | None = None

    raw_record: dict = Field(default_factory=dict)

    quality_status: QualityStatus = QualityStatus.VALID


class CanonicalSettlement(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int

    settlement_id: str
    payment_id: str | None
    reference: str
    gross_amount: Decimal
    fee: Decimal
    tax: Decimal
    adjustment: Decimal
    net_amount: Decimal
    event_timestamp: datetime
    status: str
    utr: str | None = None

    raw_reference: str | None = None
    normalized_reference: str | None = None

    raw_record: dict = Field(default_factory=dict)

    quality_status: QualityStatus = QualityStatus.VALID


class CanonicalBankEntry(BaseModel):
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int

    transaction_id: str
    narration: str
    normalized_narration: str
    credit: Decimal
    debit: Decimal
    event_timestamp: datetime
    currency: str
    utr: str | None = None

    raw_record: dict = Field(default_factory=dict)

    quality_status: QualityStatus = QualityStatus.VALID