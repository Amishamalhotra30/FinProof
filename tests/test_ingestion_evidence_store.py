from app.ingestion.coordinator import (
    MultiSourceInput,
    ingest_sources,
)
from app.ingestion.evidence_store import (
    EvidenceStore,
)


def test_evidence_store_indexes_records():

    sources = MultiSourceInput(
        payments=[
            {
                "payment_id": "PAY_001",
                "order_ref": "ORDER_001",
                "amount": "50000.00",
                "captured_on": (
                    "2026-08-31T10:00:00"
                ),
                "payment_status": "CAPTURED",
                "currency_code": "INR",
            },
        ],
    )

    result = ingest_sources(sources)

    store = EvidenceStore(result)

    assert store.count == 1

    payments = store.by_source_type(
        "payment"
    )

    assert len(payments) == 1
    assert payments[0].payment_id == "PAY_001"


def test_evidence_store_lookup_by_reference():

    sources = MultiSourceInput(
        payments=[
            {
                "payment_id": "PAY_001",
                "order_ref": "ORDER_001",
                "amount": "50000.00",
                "captured_on": (
                    "2026-08-31T10:00:00"
                ),
                "payment_status": "CAPTURED",
                "currency_code": "INR",
            },
        ],
    )

    result = ingest_sources(sources)

    store = EvidenceStore(result)

    records = store.by_reference(
        " order_001 "
    )

    assert len(records) == 1
    assert records[0].payment_id == "PAY_001"


def test_evidence_store_get_by_evidence_id():

    sources = MultiSourceInput(
        payments=[
            {
                "payment_id": "PAY_001",
                "order_ref": "ORDER_001",
                "amount": "50000.00",
                "captured_on": (
                    "2026-08-31T10:00:00"
                ),
                "payment_status": "CAPTURED",
                "currency_code": "INR",
            },
        ],
    )

    result = ingest_sources(sources)

    store = EvidenceStore(result)

    record = store.by_source_type(
        "payment"
    )[0]

    found = store.get(
        record.evidence_id
    )

    assert found is record


def test_unknown_evidence_returns_none():

    sources = MultiSourceInput()

    result = ingest_sources(sources)

    store = EvidenceStore(result)

    assert (
        store.get("DOES_NOT_EXIST")
        is None
    )