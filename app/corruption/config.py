from app.corruption.plan import CorruptionPlan


DEFAULT_CORRUPTION_PLAN = CorruptionPlan(
    missing_records=10,
    duplicate_records=5,
    amount_mismatches=5,
    reference_mismatches=5,
    timing_anomalies=5,
)