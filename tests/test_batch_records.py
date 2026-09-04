from app.generator.batch_records import (
    generate_batch_source_records,
)
from app.generator.generator import generate_batch


def test_generate_batch_source_records():
    batch = generate_batch(
        num_cases=100,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    assert len(records["orders"]) == 100
    assert len(records["payments"]) == 100
    assert len(records["refunds"]) == 100
    assert len(records["fees"]) == 100

    assert len(records["settlements"]) >= 100
    assert len(records["bank"]) >= 100
def test_batch_settlement_and_bank_totals_match():
    batch = generate_batch(
        num_cases=100,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    settlement_total = sum(
        record.net_amount
        for record in records["settlements"]
    )

    bank_total = sum(
        record.credit
        for record in records["bank"]
    )

    assert settlement_total == bank_total
def test_batch_record_count_reflects_split_settlements():
    batch = generate_batch(
        num_cases=100,
        seed=42,
    )

    split_case_count = sum(
        1
        for case in batch.cases
        if case.scenario == "SPLIT_SETTLEMENT"
    )

    records = generate_batch_source_records(batch)

    expected_settlements = (
        100 + split_case_count
    )

    assert len(records["settlements"]) == expected_settlements
    assert len(records["bank"]) == expected_settlements