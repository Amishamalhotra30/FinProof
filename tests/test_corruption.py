from app.corruption.engine import CorruptionEngine
from app.corruption.models import CorruptionType
from app.generator.batch_records import (
    generate_batch_source_records,
)
from app.generator.generator import generate_batch
from datetime import timedelta

def test_remove_bank_record():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_bank_count = len(records["bank"])

    engine = CorruptionEngine(seed=100)

    corrupted, corruption = engine.remove_bank_record(
        records,
        case_id="CASE_0001",
    )

    assert len(corrupted["bank"]) == (
        original_bank_count - 1
    )

    assert corruption.case_id == "CASE_0001"

    assert (
        corruption.corruption_type
        == CorruptionType.MISSING_RECORD
    )

    assert corruption.record_type == "bank"
def test_corruption_does_not_modify_original():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_bank_count = len(records["bank"])

    engine = CorruptionEngine(seed=100)

    corrupted, _ = engine.remove_bank_record(
        records,
        case_id="CASE_0001",
    )

    assert len(records["bank"]) == original_bank_count
    assert len(corrupted["bank"]) == (
        original_bank_count - 1
    )
def test_duplicate_bank_record():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_bank_count = len(records["bank"])

    engine = CorruptionEngine(seed=100)

    corrupted, corruption = engine.duplicate_bank_record(
        records,
        case_id="CASE_0001",
    )

    assert len(corrupted["bank"]) == (
        original_bank_count + 1
    )

    assert (
        corruption.corruption_type
        == CorruptionType.DUPLICATE_RECORD
    )

    assert corruption.record_type == "bank"
def test_change_bank_amount():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_credit = next(
        record.credit
        for record in records["bank"]
        if "CASE_0001" in record.bank_txn_id
    )

    engine = CorruptionEngine(seed=100)

    corrupted, corruption = engine.change_bank_amount(
        records,
        case_id="CASE_0001",
        difference=-1000,
    )

    corrupted_credit = next(
        record.credit
        for record in corrupted["bank"]
        if "CASE_0001" in record.bank_txn_id
    )

    assert corrupted_credit == (
        original_credit - 1000
    )

    assert (
        corruption.corruption_type
        == CorruptionType.AMOUNT_MISMATCH
    )

    assert corruption.record_type == "bank"
def test_amount_corruption_does_not_modify_original():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_credit = next(
        record.credit
        for record in records["bank"]
        if "CASE_0001" in record.bank_txn_id
    )

    engine = CorruptionEngine(seed=100)

    corrupted, _ = engine.change_bank_amount(
        records,
        case_id="CASE_0001",
        difference=-1000,
    )

    remaining_credit = next(
        record.credit
        for record in records["bank"]
        if "CASE_0001" in record.bank_txn_id
    )

    assert remaining_credit == original_credit
def test_change_settlement_reference():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_payment_id = next(
        record.payment_id
        for record in records["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    engine = CorruptionEngine(seed=100)

    corrupted, corruption = (
        engine.change_settlement_reference(
            records,
            case_id="CASE_0001",
            wrong_payment_id="CASE_0002_PAYMENT",
        )
    )

    corrupted_payment_id = next(
        record.payment_id
        for record in corrupted["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    assert original_payment_id == "CASE_0001_PAYMENT"

    assert corrupted_payment_id == "CASE_0002_PAYMENT"

    assert (
        corruption.corruption_type
        == CorruptionType.REFERENCE_MISMATCH
    )

    assert corruption.record_type == "settlement"
def test_reference_corruption_does_not_modify_original():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    engine = CorruptionEngine(seed=100)

    corrupted, _ = engine.change_settlement_reference(
        records,
        case_id="CASE_0001",
        wrong_payment_id="CASE_0002_PAYMENT",
    )

    original_payment_id = next(
        record.payment_id
        for record in records["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    corrupted_payment_id = next(
        record.payment_id
        for record in corrupted["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    assert original_payment_id == "CASE_0001_PAYMENT"
    assert corrupted_payment_id == "CASE_0002_PAYMENT"
def test_reference_corruption_rejects_same_reference():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    engine = CorruptionEngine(seed=100)

    try:
        engine.change_settlement_reference(
            records,
            case_id="CASE_0001",
            wrong_payment_id="CASE_0001_PAYMENT",
        )
    except ValueError as exc:
        assert "must differ" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for identical reference"
        )
def test_shift_settlement_time():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_time = next(
        record.settled_at
        for record in records["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    engine = CorruptionEngine(seed=100)

    corrupted, corruption = engine.shift_settlement_time(
        records,
        case_id="CASE_0001",
        minutes=60,
    )

    corrupted_time = next(
        record.settled_at
        for record in corrupted["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    assert corrupted_time == (
        original_time + timedelta(minutes=60)
    )

    assert (
        corruption.corruption_type
        == CorruptionType.TIMING_ANOMALY
    )

    assert corruption.record_type == "settlement"
def test_timing_corruption_does_not_modify_original():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_time = next(
        record.settled_at
        for record in records["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    engine = CorruptionEngine(seed=100)

    corrupted, _ = engine.shift_settlement_time(
        records,
        case_id="CASE_0001",
        minutes=60,
    )

    unchanged_time = next(
        record.settled_at
        for record in records["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    corrupted_time = next(
        record.settled_at
        for record in corrupted["settlements"]
        if "CASE_0001" in record.settlement_id
    )

    assert unchanged_time == original_time

    assert corrupted_time == (
        original_time + timedelta(minutes=60)
    )
def test_timing_corruption_rejects_zero_shift():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    engine = CorruptionEngine(seed=100)

    try:
        engine.shift_settlement_time(
            records,
            case_id="CASE_0001",
            minutes=0,
        )
    except ValueError as exc:
        assert "non-zero" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for zero time shift"
        )