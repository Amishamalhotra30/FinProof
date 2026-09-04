from typing import Any
from typing import Any, Callable
from typing import Any, Callable

from app.ingestion.quality_assessor import assess_quality
from app.ingestion.result import IngestionResult
from app.ingestion.validators import validate_record
from app.ingestion.validation_schema import (
    ADJUSTMENT_SCHEMA,
    BANK_SCHEMA,
    FEE_SCHEMA,
    ORDER_SCHEMA,
    PAYMENT_SCHEMA,
    REFUND_SCHEMA,
    SETTLEMENT_SCHEMA,
)
from app.ingestion.quality_assessor import assess_quality
from app.ingestion.result import IngestionResult

from app.ingestion.canonical_models import (
    CanonicalAdjustment,
    CanonicalBankEntry,
    CanonicalFee,
    CanonicalOrder,
    CanonicalPayment,
    CanonicalRefund,
    CanonicalSettlement,
)
from app.ingestion.normalizers import (
    normalize_adjustment,
    normalize_bank_entry,
    normalize_fee,
    normalize_order,
    normalize_payment,
    normalize_refund,
    normalize_settlement,
)
from app.ingestion.parsers import (
    parse_adjustment,
    parse_bank_statement_line,
    parse_fee,
    parse_order,
    parse_payment,
    parse_refund,
    parse_settlement,
)


def ingest_order(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> CanonicalOrder:

    raw = parse_order(data)

    return normalize_order(
        raw,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_payment(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> CanonicalPayment:

    raw = parse_payment(data)

    return normalize_payment(
        raw,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_refund(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> CanonicalRefund:

    raw = parse_refund(data)

    return normalize_refund(
        raw,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_fee(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> CanonicalFee:

    raw = parse_fee(data)

    return normalize_fee(
        raw,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_adjustment(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> CanonicalAdjustment:

    raw = parse_adjustment(data)

    return normalize_adjustment(
        raw,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_settlement(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> CanonicalSettlement:

    raw = parse_settlement(data)

    return normalize_settlement(
        raw,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_bank_statement_line(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> CanonicalBankEntry:

    raw = parse_bank_statement_line(data)

    return normalize_bank_entry(
        raw,
        source_file=source_file,
        source_row=source_row,
    )
def _ingest_with_quality(
    data: dict[str, Any],
    parser: Callable,
    normalizer: Callable,
    schema,
    source_file: str,
    source_row: int,
) -> IngestionResult:

    raw = parser(data)

    errors = validate_record(
        raw,
        required_fields=schema.required_fields,
        amount_fields=schema.amount_fields,
        timestamp_fields=schema.timestamp_fields,
    )

    quality_status = assess_quality(errors)

    if quality_status.value == "INVALID":
        return IngestionResult(
            record=None,
            quality_status=quality_status,
            errors=errors,
        )

    canonical = normalizer(
        raw,
        source_file=source_file,
        source_row=source_row,
    )

    canonical.quality_status = quality_status

    return IngestionResult(
        record=canonical,
        quality_status=quality_status,
        errors=errors,
    )
def ingest_order_with_quality(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> IngestionResult:

    return _ingest_with_quality(
        data=data,
        parser=parse_order,
        normalizer=normalize_order,
        schema=ORDER_SCHEMA,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_payment_with_quality(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> IngestionResult:

    return _ingest_with_quality(
        data=data,
        parser=parse_payment,
        normalizer=normalize_payment,
        schema=PAYMENT_SCHEMA,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_refund_with_quality(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> IngestionResult:

    return _ingest_with_quality(
        data=data,
        parser=parse_refund,
        normalizer=normalize_refund,
        schema=REFUND_SCHEMA,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_fee_with_quality(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> IngestionResult:

    return _ingest_with_quality(
        data=data,
        parser=parse_fee,
        normalizer=normalize_fee,
        schema=FEE_SCHEMA,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_adjustment_with_quality(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> IngestionResult:

    return _ingest_with_quality(
        data=data,
        parser=parse_adjustment,
        normalizer=normalize_adjustment,
        schema=ADJUSTMENT_SCHEMA,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_settlement_with_quality(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> IngestionResult:

    return _ingest_with_quality(
        data=data,
        parser=parse_settlement,
        normalizer=normalize_settlement,
        schema=SETTLEMENT_SCHEMA,
        source_file=source_file,
        source_row=source_row,
    )


def ingest_bank_statement_line_with_quality(
    data: dict[str, Any],
    source_file: str,
    source_row: int,
) -> IngestionResult:

    return _ingest_with_quality(
        data=data,
        parser=parse_bank_statement_line,
        normalizer=normalize_bank_entry,
        schema=BANK_SCHEMA,
        source_file=source_file,
        source_row=source_row,
    )