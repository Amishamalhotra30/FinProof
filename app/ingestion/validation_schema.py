from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationSchema:
    required_fields: list[str]
    amount_fields: list[str]
    timestamp_fields: list[str]


ORDER_SCHEMA = ValidationSchema(
    required_fields=[
        "order_id",
        "customer_id",
        "currency",
        "status",
    ],
    amount_fields=[
        "total_amount",
    ],
    timestamp_fields=[
        "created_at",
    ],
)


PAYMENT_SCHEMA = ValidationSchema(
    required_fields=[
        "payment_id",
        "order_ref",
        "payment_status",
        "currency_code",
    ],
    amount_fields=[
        "amount",
    ],
    timestamp_fields=[
        "captured_on",
    ],
)


REFUND_SCHEMA = ValidationSchema(
    required_fields=[
        "refund_id",
        "payment_ref",
        "refund_status",
    ],
    amount_fields=[
        "refund_amount",
    ],
    timestamp_fields=[
        "created_on",
    ],
)


FEE_SCHEMA = ValidationSchema(
    required_fields=[
        "fee_id",
        "payment_ref",
        "fee_status",
    ],
    amount_fields=[
        "fee_amount",
    ],
    timestamp_fields=[
        "created_on",
    ],
)


ADJUSTMENT_SCHEMA = ValidationSchema(
    required_fields=[
        "reference",
        "payment_ref",
        "type",
        "status",
    ],
    amount_fields=[
        "value",
    ],
    timestamp_fields=[
        "created_time",
    ],
)


SETTLEMENT_SCHEMA = ValidationSchema(
    required_fields=[
        "settlement_id",
        "reference",
        "status",
    ],
    amount_fields=[
        "gross",
        "fees",
        "tax",
        "adjustment",
        "net",
    ],
    timestamp_fields=[
        "processed_at",
    ],
)


BANK_SCHEMA = ValidationSchema(
    required_fields=[
        "transaction_ref",
        "narration",
        "currency",
    ],
    amount_fields=[
        "credit",
        "debit",
    ],
    timestamp_fields=[
        "value_date",
    ],
)