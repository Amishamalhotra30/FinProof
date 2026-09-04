from app.corruption.plan import CorruptionPlan
from app.corruption.planner import CorruptionPlanner
from app.corruption.models import CorruptionType
from app.generator.batch_records import (
    generate_batch_source_records,
)
from app.generator.generator import generate_batch


def test_corruption_planner_applies_plan():
    batch = generate_batch(
        num_cases=40,
        seed=42,
    )

    records = generate_batch_source_records(batch)

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

    corrupted, events = planner.apply(
        records,
        case_ids,
        plan,
    )

    assert len(events) == 10

    corruption_types = [
        event.corruption_type
        for event in events
    ]

    assert corruption_types.count(
        CorruptionType.MISSING_RECORD
    ) == 2

    assert corruption_types.count(
        CorruptionType.DUPLICATE_RECORD
    ) == 2

    assert corruption_types.count(
        CorruptionType.AMOUNT_MISMATCH
    ) == 2

    assert corruption_types.count(
        CorruptionType.REFERENCE_MISMATCH
    ) == 2

    assert corruption_types.count(
        CorruptionType.TIMING_ANOMALY
    ) == 2
def test_corruption_planner_is_deterministic():
    batch = generate_batch(
        num_cases=40,
        seed=42,
    )

    records = generate_batch_source_records(batch)

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

    planner_a = CorruptionPlanner(seed=100)

    corrupted_a, events_a = planner_a.apply(
        records,
        case_ids,
        plan,
    )

    planner_b = CorruptionPlanner(seed=100)

    corrupted_b, events_b = planner_b.apply(
        records,
        case_ids,
        plan,
    )

    assert events_a == events_b
    assert corrupted_a == corrupted_b
def test_corruption_planner_does_not_modify_original():
    batch = generate_batch(
        num_cases=40,
        seed=42,
    )

    records = generate_batch_source_records(batch)

    original_records = {
        key: list(value)
        for key, value in records.items()
    }

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

    planner.apply(
        records,
        case_ids,
        plan,
    )

    assert records == original_records