from datetime import datetime
from decimal import Decimal

from app.ingestion.canonical_models import (
    CanonicalAdjustment,
    CanonicalBankEntry,
    CanonicalFee,
    CanonicalOrder,
    CanonicalPayment,
    CanonicalRefund,
    CanonicalSettlement,
)
from app.ingestion.raw_models import (
    RawAdjustmentRecord,
    RawBankStatementLine,
    RawFeeRecord,
    RawOrderRecord,
    RawPaymentRecord,
    RawRefundRecord,
    RawSettlementRecord,
)


def normalize_reference(
    value: str | None,
) -> str | None:

    if value is None:
        return None

    normalized = value.strip().upper()

    return normalized or None


def normalize_currency(
    value: str,
) -> str:

    return value.strip().upper()


def normalize_narration(
    value: str,
) -> str:

    return " ".join(
        value.strip().upper().split()
    )


def normalize_timestamp(
    value: datetime,
) -> datetime:

    return value


def normalize_amount(
    value: Decimal,
) -> Decimal:

    return value.quantize(
        Decimal("0.01")
    )


def normalize_order(
    record: RawOrderRecord,
    source_file: str,
    source_row: int,
) -> CanonicalOrder:

    return CanonicalOrder(
        evidence_id=(
            f"{source_file}:"
            f"{source_row}:"
            f"{record.order_id}"
        ),
        source_type="order",
        source_file=source_file,
        source_row=source_row,
        order_id=record.order_id.strip(),
        customer_id=record.customer_id.strip(),
        amount=normalize_amount(
            record.total_amount
        ),
        currency=normalize_currency(
            record.currency
        ),
        event_timestamp=normalize_timestamp(
            record.created_at
        ),
        status=record.status.strip().upper(),
        raw_reference=record.order_id,
        normalized_reference=normalize_reference(
            record.order_id
        ),
        raw_record=record.model_dump(),
    )


def normalize_payment(
    record: RawPaymentRecord,
    source_file: str,
    source_row: int,
) -> CanonicalPayment:

    return CanonicalPayment(
        evidence_id=(
            f"{source_file}:"
            f"{source_row}:"
            f"{record.payment_id}"
        ),
        source_type="payment",
        source_file=source_file,
        source_row=source_row,
        payment_id=record.payment_id.strip(),
        order_id=record.order_ref.strip(),
        amount=normalize_amount(
            record.amount
        ),
        currency=normalize_currency(
            record.currency_code
        ),
        event_timestamp=normalize_timestamp(
            record.captured_on
        ),
        status=record.payment_status.strip().upper(),
        raw_reference=record.order_ref,
        normalized_reference=normalize_reference(
            record.order_ref
        ),
        raw_record=record.model_dump(),
    )


def normalize_refund(
    record: RawRefundRecord,
    source_file: str,
    source_row: int,
) -> CanonicalRefund:

    return CanonicalRefund(
        evidence_id=(
            f"{source_file}:"
            f"{source_row}:"
            f"{record.refund_id}"
        ),
        source_type="refund",
        source_file=source_file,
        source_row=source_row,
        refund_id=record.refund_id.strip(),
        payment_id=record.payment_ref.strip(),
        amount=normalize_amount(
            record.refund_amount
        ),
        event_timestamp=normalize_timestamp(
            record.created_on
        ),
        status=record.refund_status.strip().upper(),
        raw_reference=record.payment_ref,
        normalized_reference=normalize_reference(
            record.payment_ref
        ),
        raw_record=record.model_dump(),
    )


def normalize_fee(
    record: RawFeeRecord,
    source_file: str,
    source_row: int,
) -> CanonicalFee:

    return CanonicalFee(
        evidence_id=(
            f"{source_file}:"
            f"{source_row}:"
            f"{record.fee_id}"
        ),
        source_type="fee",
        source_file=source_file,
        source_row=source_row,
        fee_id=record.fee_id.strip(),
        payment_id=record.payment_ref.strip(),
        amount=normalize_amount(
            record.fee_amount
        ),
        event_timestamp=normalize_timestamp(
            record.created_on
        ),
        status=record.fee_status.strip().upper(),
        raw_reference=record.payment_ref,
        normalized_reference=normalize_reference(
            record.payment_ref
        ),
        raw_record=record.model_dump(),
    )


def normalize_adjustment(
    record: RawAdjustmentRecord,
    source_file: str,
    source_row: int,
) -> CanonicalAdjustment:

    return CanonicalAdjustment(
        evidence_id=(
            f"{source_file}:"
            f"{source_row}:"
            f"{record.reference}"
        ),
        source_type="adjustment",
        source_file=source_file,
        source_row=source_row,
        event_id=record.reference.strip(),
        payment_id=record.payment_ref.strip(),
        event_type=record.type.strip().upper(),
        amount=normalize_amount(
            record.value
        ),
        event_timestamp=normalize_timestamp(
            record.created_time
        ),
        status=record.status.strip().upper(),
        raw_reference=record.payment_ref,
        normalized_reference=normalize_reference(
            record.payment_ref
        ),
        raw_record=record.model_dump(),
    )


def normalize_settlement(
    record: RawSettlementRecord,
    source_file: str,
    source_row: int,
) -> CanonicalSettlement:

    return CanonicalSettlement(
        evidence_id=(
            f"{source_file}:"
            f"{source_row}:"
            f"{record.settlement_id}"
        ),
        source_type="settlement",
        source_file=source_file,
        source_row=source_row,
        settlement_id=record.settlement_id.strip(),
        payment_id=(
            record.payment_ref.strip()
            if record.payment_ref is not None
            else None
        ),
        reference=record.reference.strip(),
        gross_amount=normalize_amount(
            record.gross
        ),
        fee=normalize_amount(
            record.fees
        ),
        tax=normalize_amount(
            record.tax
        ),
        adjustment=normalize_amount(
            record.adjustment
        ),
        net_amount=normalize_amount(
            record.net
        ),
        event_timestamp=normalize_timestamp(
            record.processed_at
        ),
        status=record.status.strip().upper(),
        utr=normalize_reference(
            record.utr
        ),
        raw_reference=record.reference,
        normalized_reference=normalize_reference(
            record.reference
        ),
        raw_record=record.model_dump(),
    )


def normalize_bank_entry(
    record: RawBankStatementLine,
    source_file: str,
    source_row: int,
) -> CanonicalBankEntry:

    return CanonicalBankEntry(
        evidence_id=(
            f"{source_file}:"
            f"{source_row}:"
            f"{record.transaction_ref}"
        ),
        source_type="bank",
        source_file=source_file,
        source_row=source_row,
        transaction_id=record.transaction_ref.strip(),
        narration=record.narration,
        normalized_narration=normalize_narration(
            record.narration
        ),
        credit=normalize_amount(
            record.credit
        ),
        debit=normalize_amount(
            record.debit
        ),
        event_timestamp=normalize_timestamp(
            record.value_date
        ),
        currency=normalize_currency(
            record.currency
        ),
        utr=normalize_reference(
            record.utr
        ),
        raw_record=record.model_dump(),
    )