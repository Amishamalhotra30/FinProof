from app.ingestion.batch import ingest_batch
from app.ingestion.pipeline import (
    ingest_payment_with_quality,
)


def valid_payment(payment_id: str):
    return {
        "payment_id": payment_id,
        "order_ref": "ORDER_001",
        "amount": "50000.00",
        "captured_on": "2026-08-31T10:00:00",
        "payment_status": "CAPTURED",
        "currency_code": "INR",
    }


def test_batch_ingestion_processes_all_rows():

    result = ingest_batch(
        rows=[
            valid_payment("PAY_001"),
            valid_payment("PAY_002"),
            valid_payment("PAY_003"),
        ],
        ingest_function=ingest_payment_with_quality,
        source_file="payments.csv",
    )

    assert result.total_records == 3
    assert result.valid_count == 3
    assert result.invalid_count == 0
    assert len(result.valid_records) == 3
    assert result.errors == []


def test_batch_ingestion_keeps_invalid_rows():

    invalid = valid_payment("")

    result = ingest_batch(
        rows=[
            valid_payment("PAY_001"),
            invalid,
            valid_payment("PAY_003"),
        ],
        ingest_function=ingest_payment_with_quality,
        source_file="payments.csv",
    )

    assert result.total_records == 3
    assert result.valid_count == 2
    assert result.invalid_count == 1

    assert len(result.valid_records) == 2
    assert len(result.invalid_records) == 1
    assert len(result.errors) >= 1


def test_batch_ingestion_preserves_source_rows():

    result = ingest_batch(
        rows=[
            valid_payment("PAY_001"),
            valid_payment("PAY_002"),
        ],
        ingest_function=ingest_payment_with_quality,
        source_file="payments.csv",
        start_row=10,
    )

    assert (
        result.valid_records[0].source_row
        == 10
    )

    assert (
        result.valid_records[1].source_row
        == 11
    )