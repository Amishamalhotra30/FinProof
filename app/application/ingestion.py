from __future__ import annotations

from typing import Any

from app.generator.batch_records import generate_batch_source_records
from app.generator.generator import generate_batch
from app.ingestion.coordinator import (
    MultiSourceInput,
    MultiSourceIngestionResult,
    ingest_sources,
)


REQUIRED_SOURCE_TYPES = (
    "orders",
    "payments",
    "refunds",
    "fees",
    "adjustments",
    "settlements",
    "bank",
)


def _record_dict(record: Any) -> dict[str, Any]:
    """
    Convert a generated domain record into a dictionary.

    Plain dictionaries are passed through unchanged.
    """

    if isinstance(record, dict):
        return dict(record)

    model_dump = getattr(record, "model_dump", None)

    if callable(model_dump):
        return model_dump()

    raise TypeError(
        f"Unsupported demo record type: {type(record).__name__}"
    )


def _to_ingestion_record(
    source_type: str,
    record: Any,
) -> dict[str, Any]:
    """
    Adapt deterministic generator records to the raw-source schema
    expected by the production ingestion pipeline.
    """

    data = _record_dict(record)

    if source_type == "orders":
        return {
        "order_id": data["order_id"],
        "customer_id": data["customer_id"],
        "total_amount": data["amount"],           "amount": data["amount"],            "amount": data["amount"],
        "created_at": data["timestamp"],
        "currency": data["currency"],
        "status": data["status"],
        }

    if source_type == "payments":
        return {
            "payment_id": data["payment_id"],
            "order_ref": data["order_id"],
            "amount": data["amount"],
            "captured_on": data["captured_at"],
            "payment_status": data["status"],
            "currency_code": "INR",
        }

    if source_type == "refunds":
        return {
            "refund_id": data["refund_id"],
            "payment_ref": data["payment_id"],
            "refund_amount": data["amount"],
            "created_on": data["timestamp"],
            "reference": data.get("reference"),
            "refund_status": data["status"],
        }

    if source_type == "fees":
        return {
            "fee_id": data["fee_id"],
            "payment_ref": data["payment_id"],
            "fee_amount": data["amount"],
            "created_on": data["timestamp"],
            "fee_status": data["status"],
        }

    if source_type == "adjustments":
        return {
            "reference": data["reference"],
            "payment_ref": data["payment_id"],
            "type": data["type"],
            "value": data["amount"],
            "created_time": data["timestamp"],
            "status": data["status"],
        }

    if source_type == "settlements":
        return {
            "settlement_id": data["settlement_id"],
            "payment_ref": data.get("payment_id"),
            "reference": data["reference"],
            "gross": data["gross_amount"],
            "fees": data["fee"],
            "tax": data["tax"],
            "adjustment": data["adjustment"],
            "net": data["net_amount"],
            "processed_at": data["settled_at"],
            "status": data["status"],
            "utr": data.get("utr"),
        }

    if source_type == "bank":
        return {
            "transaction_ref": data["bank_txn_id"],
            "narration": data["narration"],
            "credit": data["credit"],
            "debit": data["debit"],
            "value_date": data["value_date"],
            "currency": "INR",
            "utr": data.get("utr"),
        }

    raise ValueError(
        f"Unsupported demo source type: {source_type}"
    )


def build_ingestion_input(
    records: dict[str, list[Any]],
) -> MultiSourceInput:
    """
    Convert application source records into the existing
    MultiSourceInput boundary.

    Missing source types are treated as empty sources.
    """

    return MultiSourceInput(
        orders=[
            _to_ingestion_record("orders", record)
            for record in records.get("orders", [])
        ],
        payments=[
            _to_ingestion_record("payments", record)
            for record in records.get("payments", [])
        ],
        refunds=[
            _to_ingestion_record("refunds", record)
            for record in records.get("refunds", [])
        ],
        fees=[
            _to_ingestion_record("fees", record)
            for record in records.get("fees", [])
        ],
        adjustments=[
            _to_ingestion_record("adjustments", record)
            for record in records.get("adjustments", [])
        ],
        settlements=[
            _to_ingestion_record("settlements", record)
            for record in records.get("settlements", [])
        ],
        bank=[
            _to_ingestion_record("bank", record)
            for record in records.get("bank", [])
        ],
    )


def ingest_records(
    records: dict[str, list[Any]],
) -> MultiSourceIngestionResult:
    """
    Run the existing production ingestion pipeline.

    Validation, parsing, normalization, and quality assessment
    remain owned by app.ingestion.
    """

    sources = build_ingestion_input(records)

    return ingest_sources(sources)


def generate_demo_records(
    *,
    num_cases: int = 100,
    seed: int = 42,
) -> dict[str, list[Any]]:
    """
    Generate deterministic demo source records.

    This deliberately uses the underlying generator instead of
    app.benchmark so benchmark ground truth and corruption metadata
    never enter the application runtime.
    """

    generated_batch = generate_batch(
        num_cases=num_cases,
        seed=seed,
    )

    return generate_batch_source_records(
        generated_batch
    )


def generate_demo_ingestion(
    *,
    num_cases: int = 100,
    seed: int = 42,
) -> MultiSourceIngestionResult:
    """
    Generate and ingest deterministic demo records.
    """

    records = generate_demo_records(
        num_cases=num_cases,
        seed=seed,
    )

    return ingest_records(records)
