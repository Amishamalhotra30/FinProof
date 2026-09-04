from app.ingestion.pipeline import (
    ingest_payment_with_quality,
)
from app.ingestion.quality import QualityStatus


def test_valid_payment_passes_quality_gate():

    result = ingest_payment_with_quality(
        {
            "payment_id": "PAY_001",
            "order_ref": "ORDER_001",
            "amount": "50000.00",
            "captured_on": "2026-08-31T10:00:00",
            "payment_status": "CAPTURED",
            "currency_code": "INR",
        },
        source_file="payments.csv",
        source_row=10,
    )

    assert result.quality_status == QualityStatus.VALID
    assert result.errors == []
    assert result.record is not None


def test_invalid_payment_is_rejected():

    result = ingest_payment_with_quality(
        {
            "payment_id": "",
            "order_ref": "ORDER_001",
            "amount": "-500.00",
            "captured_on": "2026-08-31T10:00:00",
            "payment_status": "CAPTURED",
            "currency_code": "INR",
        },
        source_file="payments.csv",
        source_row=11,
    )

    assert (
        result.quality_status
        == QualityStatus.INVALID
    )

    assert result.record is None
    assert len(result.errors) >= 2