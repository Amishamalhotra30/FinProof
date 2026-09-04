from decimal import Decimal

from app.reconciliation.matcher import reconcile_case
from app.reconciliation.models import MatchStatus
from app.generator.batch_records import (
    generate_batch_source_records,
)
from app.generator.generator import generate_batch
from app.reconciliation.controller import (
    reconcile_records,
)
from app.reconciliation.models import MatchStatus
from app.corruption.plan import CorruptionPlan
from app.corruption.planner import CorruptionPlanner

def test_reconcile_matching_case():
    result = reconcile_case(
        case_id="CASE_0001",
        payment_amount=Decimal("50000.00"),
        refund_amount=Decimal("5000.00"),
        fee_amount=Decimal("1000.00"),
        settlement_amount=Decimal("44000.00"),
        bank_amount=Decimal("44000.00"),
    )

    assert result.status == MatchStatus.MATCH
    assert result.confidence == Decimal("1.00")


def test_reconcile_settlement_mismatch():
    result = reconcile_case(
        case_id="CASE_0001",
        payment_amount=Decimal("50000.00"),
        refund_amount=Decimal("5000.00"),
        fee_amount=Decimal("1000.00"),
        settlement_amount=Decimal("43000.00"),
        bank_amount=Decimal("43000.00"),
    )

    assert result.status == MatchStatus.EXCEPTION
    assert "Settlement amount" in result.reason


def test_reconcile_bank_mismatch():
    result = reconcile_case(
        case_id="CASE_0001",
        payment_amount=Decimal("50000.00"),
        refund_amount=Decimal("5000.00"),
        fee_amount=Decimal("1000.00"),
        settlement_amount=Decimal("44000.00"),
        bank_amount=Decimal("43000.00"),
    )

    assert result.status == MatchStatus.EXCEPTION
    assert "Bank credit" in result.reason
def test_reconcile_entire_batch():
    batch = generate_batch(
        num_cases=20,
        seed=42,
    )

    records = generate_batch_source_records(
        batch
    )

    results = reconcile_records(records)

    assert len(results) == 20
def test_clean_batch_all_matches():
    batch = generate_batch(
        num_cases=20,
        seed=42,
    )

    records = generate_batch_source_records(
        batch
    )

    results = reconcile_records(records)

    assert all(
        result.status == MatchStatus.MATCH
        for result in results
    )
def test_reconcile_corrupted_batch():
    batch = generate_batch(
        num_cases=40,
        seed=42,
    )

    records = generate_batch_source_records(
        batch
    )

    case_ids = [
        case.case_id
        for case in batch.cases
    ]

    plan = CorruptionPlan(
        missing_records=2,
        duplicate_records=2,
        amount_mismatches=2,
        reference_mismatches=2,
        timing_anomalies=2,
    )

    planner = CorruptionPlanner(seed=100)

    corrupted_records, events = planner.apply(
        records,
        case_ids,
        plan,
    )

    results = reconcile_records(
        corrupted_records
    )

    exceptions = [
        result
        for result in results
        if result.status == MatchStatus.EXCEPTION
    ]

    assert len(exceptions) > 0