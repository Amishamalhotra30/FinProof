from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OrderRecord(BaseModel):
    order_id: str
    customer_id: str
    amount: Decimal
    currency: str
    timestamp: datetime
    payment_id: str | None = None
    status: str


class PaymentRecord(BaseModel):
    payment_id: str
    order_id: str
    amount: Decimal
    status: str
    captured_at: datetime
    method: str


class RefundRecord(BaseModel):
    refund_id: str
    payment_id: str
    amount: Decimal
    timestamp: datetime
    reference: str | None = None
    status: str


class FeeRecord(BaseModel):
    fee_id: str
    payment_id: str
    amount: Decimal
    timestamp: datetime
    status: str


class AdjustmentRecord(BaseModel):
    event_id: str
    payment_id: str
    event_type: str
    amount: Decimal
    timestamp: datetime
    reference: str | None = None
    status: str


class SettlementRecord(BaseModel):
    settlement_id: str
    payment_id: str | None = None
    reference: str
    gross_amount: Decimal
    fee: Decimal
    tax: Decimal
    adjustment: Decimal
    net_amount: Decimal
    status: str
    settled_at: datetime
    utr: str | None = None


class BankStatementLine(BaseModel):
    bank_txn_id: str
    value_date: datetime
    narration: str
    credit: Decimal
    debit: Decimal
    utr: str | None = None
    balance: Decimal