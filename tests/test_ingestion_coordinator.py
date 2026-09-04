from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)


def payment(payment_id: str):
    return {
        "payment_id": payment_id,
        "order_ref": "ORDER_001",
        "amount": "50000.00",
        "captured_on": "2026-08-31T10:00:00",
        "payment_status": "CAPTURED",
        "currency_code": "INR",
    }


def bank_line(transaction_id: str):
    return {
        "transaction_ref": transaction_id,
        "narration": "Settlement credit",
        "credit": "44000.00",
        "debit": "0.00",
        "value_date": "2026-08-31T10:15:00",
        "currency": "INR",
        "utr": "UTR001",
    }


def test_multi_source_ingestion():

    sources = MultiSourceInput(
        payments=[
            payment("PAY_001"),
            payment("PAY_002"),
        ],
        bank=[
            bank_line("BANK_001"),
        ],
    )

    result = ingest_sources(sources)

    assert result.total_records == 3

    assert result.payments.valid_count == 2
    assert result.bank.valid_count == 1

    assert result.payments.invalid_count == 0
    assert result.bank.invalid_count == 0

    assert result.errors == []


def test_multi_source_ingestion_isolates_invalid_rows():

    sources = MultiSourceInput(
        payments=[
            payment("PAY_001"),
            payment(""),
            payment("PAY_003"),
        ],
        bank=[
            bank_line("BANK_001"),
        ],
    )

    result = ingest_sources(sources)

    assert result.total_records == 4

    assert result.payments.valid_count == 2
    assert result.payments.invalid_count == 1

    assert result.bank.valid_count == 1
    assert result.bank.invalid_count == 0

    assert len(result.errors) >= 1


def test_sources_are_kept_separate():

    sources = MultiSourceInput(
        payments=[
            payment("PAY_001"),
        ],
        bank=[
            bank_line("BANK_001"),
        ],
    )

    result = ingest_sources(sources)

    assert len(result.payments.valid_records) == 1
    assert len(result.bank.valid_records) == 1

    assert (
        result.payments.valid_records[0].payment_id
        == "PAY_001"
    )

    assert (
        result.bank.valid_records[0].transaction_id
        == "BANK_001"
    )