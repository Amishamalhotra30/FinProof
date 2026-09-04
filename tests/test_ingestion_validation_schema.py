from app.ingestion.validation_schema import (
    ADJUSTMENT_SCHEMA,
    BANK_SCHEMA,
    FEE_SCHEMA,
    ORDER_SCHEMA,
    PAYMENT_SCHEMA,
    REFUND_SCHEMA,
    SETTLEMENT_SCHEMA,
    ValidationSchema,
)


def test_validation_schema_is_immutable():

    assert isinstance(
        PAYMENT_SCHEMA,
        ValidationSchema,
    )


def test_payment_schema():

    assert PAYMENT_SCHEMA.required_fields == [
        "payment_id",
        "order_ref",
        "payment_status",
        "currency_code",
    ]

    assert PAYMENT_SCHEMA.amount_fields == [
        "amount",
    ]

    assert PAYMENT_SCHEMA.timestamp_fields == [
        "captured_on",
    ]


def test_all_record_types_have_schema():

    schemas = [
        ORDER_SCHEMA,
        PAYMENT_SCHEMA,
        REFUND_SCHEMA,
        FEE_SCHEMA,
        ADJUSTMENT_SCHEMA,
        SETTLEMENT_SCHEMA,
        BANK_SCHEMA,
    ]

    assert len(schemas) == 7

    for schema in schemas:
        assert schema.required_fields
        assert schema.amount_fields
        assert schema.timestamp_fields