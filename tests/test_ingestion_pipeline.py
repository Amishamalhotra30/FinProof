from app.ingestion.pipeline import (
    ingest_bank_statement_line,
    ingest_payment,
)


def test_ingest_payment_end_to_end():

    payment = ingest_payment(
        {
            "payment_id": " PAY_001 ",
            "order_ref": " ORDER_001 ",
            "amount": "50000.00",
            "captured_on": "2026-08-31T10:00:00",
            "payment_status": " captured ",
            "currency_code": "inr",
        },
        source_file="payments.csv",
        source_row=15,
    )

    assert payment.payment_id == "PAY_001"
    assert payment.order_id == "ORDER_001"
    assert payment.amount == 50000
    assert payment.currency == "INR"
    assert payment.status == "CAPTURED"

    assert payment.source_file == "payments.csv"
    assert payment.source_row == 15

    assert payment.evidence_id == (
        "payments.csv:15: PAY_001 "
    )


def test_ingest_bank_line_end_to_end():

    bank = ingest_bank_statement_line(
        {
            "transaction_ref": " BANK_001 ",
            "narration": (
                " Settlement   credit CASE_001 "
            ),
            "credit": "44000.00",
            "debit": "0.00",
            "value_date": "2026-08-31T10:15:00",
            "currency": "inr",
            "utr": " utr001 ",
        },
        source_file="bank.csv",
        source_row=21,
    )

    assert bank.transaction_id == "BANK_001"

    assert (
        bank.normalized_narration
        == "SETTLEMENT CREDIT CASE_001"
    )

    assert bank.credit == 44000
    assert bank.debit == 0
    assert bank.currency == "INR"
    assert bank.utr == "UTR001"

    assert bank.source_file == "bank.csv"
    assert bank.source_row == 21