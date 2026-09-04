import pytest

from app.corruption.plan import CorruptionPlan
from app.corruption.config import DEFAULT_CORRUPTION_PLAN

def test_corruption_plan_counts_total():
    plan = CorruptionPlan(
        missing_records=10,
        duplicate_records=5,
        amount_mismatches=3,
        reference_mismatches=2,
        timing_anomalies=1,
    )

    assert plan.total_corruptions == 21
def test_default_corruption_plan():
    assert (
        DEFAULT_CORRUPTION_PLAN.total_corruptions
        == 30
    )

    assert (
        DEFAULT_CORRUPTION_PLAN.missing_records
        == 10
    )

    assert (
        DEFAULT_CORRUPTION_PLAN.duplicate_records
        == 5
    )

    assert (
        DEFAULT_CORRUPTION_PLAN.amount_mismatches
        == 5
    )

    assert (
        DEFAULT_CORRUPTION_PLAN.reference_mismatches
        == 5
    )

    assert (
        DEFAULT_CORRUPTION_PLAN.timing_anomalies
        == 5
    )