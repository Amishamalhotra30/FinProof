from app.ingestion.quality import QualityStatus
from app.ingestion.quality_assessor import assess_quality


def test_valid_record_has_valid_quality():

    assert (
        assess_quality([])
        == QualityStatus.VALID
    )


def test_validation_errors_make_record_invalid():

    errors = [
        "payment_id must be a non-empty string",
    ]

    assert (
        assess_quality(errors)
        == QualityStatus.INVALID
    )


def test_multiple_validation_errors_are_invalid():

    errors = [
        "payment_id must be a non-empty string",
        "amount must be a non-negative Decimal",
        "captured_at must be a datetime",
    ]

    assert (
        assess_quality(errors)
        == QualityStatus.INVALID
    )