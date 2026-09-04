from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class RawOrderRecord(BaseModel):
    order_id: str
    customer_id: str
    total_amount: Decimal
    created_at: datetime
    currency: str
    status: str


class RawPaymentRecord(BaseModel):
    payment_id: str
    order_ref: str
    amount: Decimal
    captured_on: datetime
    payment_status: str
    currency_code: str


class RawRefundRecord(BaseModel):
    refund_id: str
    payment_ref: str
    refund_amount: Decimal
    created_on: datetime
    reference: str | None = None
    refund_status: str


class RawFeeRecord(BaseModel):
    fee_id: str
    payment_ref: str
    fee_amount: Decimal
    created_on: datetime
    fee_status: str


class RawAdjustmentRecord(BaseModel):
    reference: str
    payment_ref: str
    type: str
    value: Decimal
    created_time: datetime
    status: str


class RawSettlementRecord(BaseModel):
    settlement_id: str
    payment_ref: str | None = None
    reference: str
    gross: Decimal
    fees: Decimal
    tax: Decimal
    adjustment: Decimal
    net: Decimal
    processed_at: datetime
    status: str
    utr: str | None = None


class RawBankStatementLine(BaseModel):
    transaction_ref: str
    narration: str
    credit: Decimal
    debit: Decimal
    value_date: datetime
    currency: str
    utr: str | None = None