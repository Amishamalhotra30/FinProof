from datetime import datetime
from decimal import Decimal

from app.ingestion.validators import (
    is_non_empty_string,
    is_valid_amount,
    is_valid_timestamp,
    validate_amount,
    validate_record,
    validate_required_string,
    validate_timestamp,
)


def test_non_empty_string_validation():

    assert is_non_empty_string("PAY_001")
    assert not is_non_empty_string("")
    assert not is_non_empty_string("   ")
    assert not is_non_empty_string(None)


def test_amount_validation():

    assert is_valid_amount(
        Decimal("100.00")
    )

    assert is_valid_amount(
        Decimal("0.00")
    )

    assert not is_valid_amount(
        Decimal("-1.00")
    )

    assert not is_valid_amount(
        "100.00"
    )


def test_timestamp_validation():

    assert is_valid_timestamp(
        datetime(2026, 8, 31, 10, 0)
    )

    assert not is_valid_timestamp(
        "2026-08-31T10:00:00"
    )


def test_required_string_validation():

    assert validate_required_string(
        "PAY_001",
        "payment_id",
    ) == []

    assert validate_required_string(
        "",
        "payment_id",
    ) == [
        "payment_id must be a non-empty string"
    ]


def test_amount_validation_errors():

    assert validate_amount(
        Decimal("-100"),
        "amount",
    ) == [
        "amount must be a non-negative Decimal"
    ]


def test_timestamp_validation_errors():

    assert validate_timestamp(
        "invalid",
        "captured_at",
    ) == [
        "captured_at must be a datetime"
    ]


def test_validate_record():

    class Record:
        payment_id = "PAY_001"
        amount = Decimal("500.00")
        captured_at = datetime(
            2026,
            8,
            31,
            10,
            0,
        )

    errors = validate_record(
        Record(),
        required_fields=[
            "payment_id",
        ],
        amount_fields=[
            "amount",
        ],
        timestamp_fields=[
            "captured_at",
        ],
    )

    assert errors == []


def test_validate_record_detects_missing_field():

    class Record:
        payment_id = "PAY_001"

    errors = validate_record(
        Record(),
        required_fields=[
            "payment_id",
            "order_id",
        ],
    )

    assert (
        "Missing required field: order_id"
        in errors
    )