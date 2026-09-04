from datetime import datetime
from decimal import Decimal

from app.ingestion.normalizers import (
    normalize_bank_entry,
    normalize_payment,
    normalize_reference,
)
from app.ingestion.raw_models import (
    RawBankStatementLine,
    RawPaymentRecord,
)


def test_normalize_reference():

    assert normalize_reference(
        " pay_001 "
    ) == "PAY_001"

    assert normalize_reference(
        "  "
    ) is None

    assert normalize_reference(
        None
    ) is None


def test_normalize_payment():

    raw = RawPaymentRecord(
        payment_id=" PAY_001 ",
        order_ref=" ORDER_001 ",
        amount=Decimal("50000"),
        captured_on=datetime(
            2026,
            8,
            31,
            10,
            0,
        ),
        payment_status=" captured ",
        currency_code="inr",
    )

    canonical = normalize_payment(
        raw,
        source_file="payments.csv",
        source_row=7,
    )

    assert canonical.payment_id == "PAY_001"
    assert canonical.order_id == "ORDER_001"
    assert canonical.amount == Decimal("50000.00")
    assert canonical.currency == "INR"
    assert canonical.status == "CAPTURED"

    assert (
        canonical.source_file
        == "payments.csv"
    )

    assert canonical.source_row == 7

    assert (
        canonical.normalized_reference
        == "ORDER_001"
    )

    assert (
        canonical.raw_record["payment_id"]
        == " PAY_001 "
    )


def test_normalize_bank_entry():

    raw = RawBankStatementLine(
        transaction_ref=" BANK_001 ",
        narration="  Settlement   credit CASE_001  ",
        credit=Decimal("44000"),
        debit=Decimal("0"),
        value_date=datetime(
            2026,
            8,
            31,
            10,
            15,
        ),
        currency="inr",
        utr=" utr001 ",
    )

    canonical = normalize_bank_entry(
        raw,
        source_file="bank.csv",
        source_row=12,
    )

    assert (
        canonical.transaction_id
        == "BANK_001"
    )

    assert (
        canonical.normalized_narration
        == "SETTLEMENT CREDIT CASE_001"
    )

    assert canonical.credit == Decimal(
        "44000.00"
    )

    assert canonical.debit == Decimal(
        "0.00"
    )

    assert canonical.currency == "INR"

    assert canonical.utr == "UTR001"

    assert canonical.source_row == 12