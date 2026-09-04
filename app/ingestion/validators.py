from datetime import datetime
from decimal import Decimal
from typing import Any


def is_non_empty_string(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
    )


def is_valid_amount(value: Any) -> bool:
    if isinstance(value, Decimal):
        return value >= Decimal("0")

    return False


def is_valid_timestamp(value: Any) -> bool:
    return isinstance(value, datetime)


def validate_required_string(
    value: Any,
    field_name: str,
) -> list[str]:

    if not is_non_empty_string(value):
        return [
            f"{field_name} must be a non-empty string"
        ]

    return []


def validate_amount(
    value: Any,
    field_name: str,
) -> list[str]:

    if not is_valid_amount(value):
        return [
            f"{field_name} must be a non-negative Decimal"
        ]

    return []


def validate_timestamp(
    value: Any,
    field_name: str,
) -> list[str]:

    if not is_valid_timestamp(value):
        return [
            f"{field_name} must be a datetime"
        ]

    return []


def validate_record(
    record: Any,
    required_fields: list[str],
    amount_fields: list[str] | None = None,
    timestamp_fields: list[str] | None = None,
) -> list[str]:

    errors: list[str] = []

    amount_fields = amount_fields or []
    timestamp_fields = timestamp_fields or []

    for field_name in required_fields:

        if not hasattr(record, field_name):
            errors.append(
                f"Missing required field: {field_name}"
            )
            continue

        value = getattr(record, field_name)

        errors.extend(
            validate_required_string(
                value,
                field_name,
            )
        )

    for field_name in amount_fields:

        if not hasattr(record, field_name):
            errors.append(
                f"Missing amount field: {field_name}"
            )
            continue

        errors.extend(
            validate_amount(
                getattr(record, field_name),
                field_name,
            )
        )

    for field_name in timestamp_fields:

        if not hasattr(record, field_name):
            errors.append(
                f"Missing timestamp field: {field_name}"
            )
            continue

        errors.extend(
            validate_timestamp(
                getattr(record, field_name),
                field_name,
            )
        )

    return errors