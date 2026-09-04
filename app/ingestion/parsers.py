from typing import Any

from app.ingestion.raw_models import (
    RawAdjustmentRecord,
    RawBankStatementLine,
    RawFeeRecord,
    RawOrderRecord,
    RawPaymentRecord,
    RawRefundRecord,
    RawSettlementRecord,
)


def parse_order(
    data: dict[str, Any],
) -> RawOrderRecord:
    return RawOrderRecord.model_validate(data)


def parse_payment(
    data: dict[str, Any],
) -> RawPaymentRecord:
    return RawPaymentRecord.model_validate(data)


def parse_refund(
    data: dict[str, Any],
) -> RawRefundRecord:
    return RawRefundRecord.model_validate(data)


def parse_fee(
    data: dict[str, Any],
) -> RawFeeRecord:
    return RawFeeRecord.model_validate(data)


def parse_adjustment(
    data: dict[str, Any],
) -> RawAdjustmentRecord:
    return RawAdjustmentRecord.model_validate(data)


def parse_settlement(
    data: dict[str, Any],
) -> RawSettlementRecord:
    return RawSettlementRecord.model_validate(data)


def parse_bank_statement_line(
    data: dict[str, Any],
) -> RawBankStatementLine:
    return RawBankStatementLine.model_validate(data)