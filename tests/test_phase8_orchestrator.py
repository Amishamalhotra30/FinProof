from decimal import Decimal

from app.evaluation.orchestrator import (
    Phase8EvaluationOrchestrator,
)
from app.evaluation.report import Phase8Report


class FakeVerification:
    total_cases = 100

    false_pass_rate = Decimal("0")
    false_fail_rate = Decimal("0")
    material_failure_detection_rate = Decimal("1")
    financial_discrepancy_coverage = Decimal("1")

    processing_time_ms = Decimal("10")
    verification_throughput = Decimal("10000")


class FakeInvestigation:
    total_cases = 100

    investigation_coverage = Decimal("1")
    full_explanation_rate = Decimal("0.5")
    false_explanation_rate = Decimal("0")
    explanation_coverage = Decimal("0.85")

    processing_time_ms = Decimal("20")
    throughput = Decimal("5000")


class FakeDecision:
    total_cases = 100

    automation_rate = Decimal("60")
    human_review_rate = Decimal("25")
    false_resolution_rate = Decimal("0")

    processing_time_ms = Decimal("5")
    throughput = Decimal("20000")


def test_phase8_orchestrator_consolidates_metrics():
    report = Phase8EvaluationOrchestrator().run(
        num_cases=100,
        seed=42,
        verification_evaluation=FakeVerification(),
        investigation_evaluation=FakeInvestigation(),
        decision_evaluation=FakeDecision(),
    )

    assert isinstance(
        report,
        Phase8Report,
    )

    assert report.benchmark_cases == 100
    assert report.verification_cases == 100
    assert report.investigation_cases == 100
    assert report.decision_cases == 100

    assert (
        report.verification_false_pass_rate
        == Decimal("0")
    )

    assert (
        report.investigation_false_explanation_rate
        == Decimal("0")
    )

    assert (
        report.decision_false_resolution_rate
        == Decimal("0")
    )


def test_phase8_safe_when_all_safety_rates_are_zero():
    report = Phase8EvaluationOrchestrator().run(
        verification_evaluation=FakeVerification(),
        investigation_evaluation=FakeInvestigation(),
        decision_evaluation=FakeDecision(),
    )

    assert report.safety_status == "SAFE"
    assert report.overall_status == "EVALUATED"


def test_phase8_requires_review_for_false_pass():
    verification = FakeVerification()
    verification.false_pass_rate = Decimal("0.01")

    report = Phase8EvaluationOrchestrator().run(
        verification_evaluation=verification,
        investigation_evaluation=FakeInvestigation(),
        decision_evaluation=FakeDecision(),
    )

    assert report.safety_status == "REVIEW_REQUIRED"
    assert report.overall_status == "REVIEW_REQUIRED"


def test_phase8_requires_review_for_false_explanation():
    investigation = FakeInvestigation()
    investigation.false_explanation_rate = Decimal(
        "0.01"
    )

    report = Phase8EvaluationOrchestrator().run(
        verification_evaluation=FakeVerification(),
        investigation_evaluation=investigation,
        decision_evaluation=FakeDecision(),
    )

    assert report.safety_status == "REVIEW_REQUIRED"


def test_phase8_requires_review_for_false_resolution():
    decision = FakeDecision()
    decision.false_resolution_rate = Decimal(
        "0.01"
    )

    report = Phase8EvaluationOrchestrator().run(
        verification_evaluation=FakeVerification(),
        investigation_evaluation=FakeInvestigation(),
        decision_evaluation=decision,
    )

    assert report.safety_status == "REVIEW_REQUIRED"


def test_phase8_supports_missing_later_phase_results():
    report = Phase8EvaluationOrchestrator().run(
        num_cases=100,
        verification_evaluation=FakeVerification(),
    )

    assert report.verification_cases == 100
    assert report.investigation_cases == 0
    assert report.decision_cases == 0

    assert report.investigation_coverage == Decimal("0")
    assert report.decision_automation_rate == Decimal("0")