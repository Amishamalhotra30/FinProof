from app.ingestion.parsers import (
    parse_bank_statement_line,
    parse_payment,
)


def test_parse_payment():

    record = parse_payment(
        {
            "payment_id": "PAY_001",
            "order_ref": "ORDER_001",
            "amount": "50000.00",
            "captured_on": "2026-08-31T10:00:00",
            "payment_status": "CAPTURED",
            "currency_code": "INR",
        }
    )

    assert record.payment_id == "PAY_001"
    assert record.order_ref == "ORDER_001"
    assert str(record.amount) == "50000.00"


def test_parse_bank_statement_line():

    record = parse_bank_statement_line(
        {
            "transaction_ref": "BANK_001",
            "narration": "Settlement credit",
            "credit": "44000.00",
            "debit": "0.00",
            "value_date": "2026-08-31T10:15:00",
            "currency": "INR",
            "utr": "UTR001",
        }
    )

    assert record.transaction_ref == "BANK_001"
    assert record.credit == 44000
    assert record.utr == "UTR001"