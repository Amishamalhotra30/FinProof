from decimal import Decimal

from app.generator.batch_records import (
    generate_batch_source_records,
)
from app.generator.generator import generate_batch
from app.reconciliation.aggregator import (
    aggregate_records,
)
from app.reconciliation.rules import (
    verify_case,
)
from app.corruption.plan import CorruptionPlan
from app.corruption.planner import CorruptionPlanner


def test_clean_case_has_no_verification_issues():

    batch = generate_batch(
        num_cases=20,
        seed=42,
    )

    records = generate_batch_source_records(
        batch
    )

    cases = aggregate_records(records)

    for case in cases.values():
        issues = verify_case(case)

        assert issues == []
def test_amount_mismatch_is_detected():

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

    planner = CorruptionPlanner(seed=100)

    corrupted, events = planner.apply(
        records,
        case_ids,
        CorruptionPlan(
            amount_mismatches=1,
        ),
    )

    cases = aggregate_records(corrupted)

    corrupted_case_id = events[0].case_id

    payment_id = (
        f"{corrupted_case_id}_PAYMENT"
    )

    issues = verify_case(
        cases[payment_id]
    )

    assert any(
        issue.rule == "BANK_AMOUNT_MISMATCH"
        for issue in issues
    )
def test_reference_mismatch_is_detected():

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

    planner = CorruptionPlanner(seed=100)

    corrupted, events = planner.apply(
        records,
        case_ids,
        CorruptionPlan(
            reference_mismatches=1,
        ),
    )

    cases = aggregate_records(corrupted)

    assert len(events) == 1

    payment_ids = list(cases.keys())

    issues_found = []

    for payment_id in payment_ids:
        issues_found.extend(
            verify_case(
                cases[payment_id]
            )
        )

    assert any(
        issue.rule == "REFERENCE_MISMATCH"
        for issue in issues_found
    )
def test_timing_anomaly_is_detected():

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

    planner = CorruptionPlanner(seed=100)

    corrupted, events = planner.apply(
        records,
        case_ids,
        CorruptionPlan(
            timing_anomalies=1,
        ),
    )

    cases = aggregate_records(corrupted)

    corrupted_case_id = events[0].case_id

    payment_id = (
        f"{corrupted_case_id}_PAYMENT"
    )

    issues = verify_case(
        cases[payment_id]
    )

    assert any(
        issue.rule == "TIMING_ANOMALY"
        for issue in issues
    )