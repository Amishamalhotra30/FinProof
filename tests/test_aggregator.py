from decimal import Decimal

from app.generator.batch_records import (
    generate_batch_source_records,
)
from app.generator.generator import generate_batch
from app.reconciliation.aggregator import (
    aggregate_records,
)


def test_aggregate_records():
    batch = generate_batch(
        num_cases=20,
        seed=42,
    )

    records = generate_batch_source_records(
        batch
    )

    cases = aggregate_records(records)

    assert len(cases) == 20
def test_case_amounts_are_aggregated():
    batch = generate_batch(
        num_cases=20,
        seed=42,
    )

    records = generate_batch_source_records(
        batch
    )

    cases = aggregate_records(records)

    for case in cases.values():
        assert case.payment is not None

        expected_settlement = (
            case.payment.amount
            - case.refund_amount
            - case.fee_amount
        )

        assert (
            case.settlement_amount
            == expected_settlement
        )
def test_split_settlement_is_aggregated():
    batch = generate_batch(
        num_cases=100,
        seed=42,
    )

    records = generate_batch_source_records(
        batch
    )

    cases = aggregate_records(records)

    split_case_ids = [
        case.case_id
        for case in batch.cases
        if case.scenario == "SPLIT_SETTLEMENT"
    ]

    assert len(split_case_ids) > 0

    for case_id in split_case_ids:
        payment_id = (
            f"{case_id}_PAYMENT"
        )

        case = cases[payment_id]

        assert len(case.settlements) == 2

        assert (
            case.settlement_amount
            == case.bank_amount
        )