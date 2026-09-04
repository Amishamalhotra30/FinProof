from decimal import Decimal

from app.decisions.metrics import (
    DecisionMetricsCalculator,
    calculate_decision_metrics,
)
from app.decisions.models import (
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResult,
    MaterialityLevel,
)


def make_decision(
    case_id: str,
    outcome: DecisionOutcome,
    financial_impact: str = "100",
) -> DecisionResult:
    return DecisionResult(
        case_id=case_id,
        decision=outcome,
        reason_code=DecisionReasonCode.ALL_CONTROLS_PASSED,
        basis=("test",),
        financial_impact=Decimal(
            financial_impact
        ),
        materiality=MaterialityLevel.NONE,
        policy_rule_id="TEST",
        evidence_sufficient=True,
        investigation_validated=True,
        contradictory_evidence=False,
        supporting_evidence_ids=[],
    )


# ============================================================
# BASIC METRICS
# ============================================================


def test_empty_decision_batch_produces_zero_metrics():
    metrics = DecisionMetricsCalculator().calculate(
        []
    )

    assert metrics.total_cases == 0
    assert metrics.auto_resolved == 0
    assert metrics.pending == 0
    assert metrics.human_review == 0
    assert metrics.blocked == 0

    assert metrics.automation_rate == Decimal("0")
    assert metrics.human_review_rate == Decimal("0")
    assert metrics.false_resolution_rate == Decimal("0")

    assert metrics.human_agreements is None
    assert metrics.human_agreement_rate is None

    assert (
        metrics.human_investigation_reduction
        == Decimal("0")
    )

    assert (
        metrics.unresolved_financial_value
        == Decimal("0")
    )


def test_decision_counts_are_calculated():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_003",
            DecisionOutcome.PENDING,
        ),
        make_decision(
            "CASE_004",
            DecisionOutcome.HUMAN_REVIEW,
        ),
        make_decision(
            "CASE_005",
            DecisionOutcome.BLOCKED,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.total_cases == 5
    assert metrics.auto_resolved == 2
    assert metrics.pending == 1
    assert metrics.human_review == 1
    assert metrics.blocked == 1


# ============================================================
# RATES
# ============================================================


def test_automation_rate_is_calculated():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_003",
            DecisionOutcome.HUMAN_REVIEW,
        ),
        make_decision(
            "CASE_004",
            DecisionOutcome.BLOCKED,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.automation_rate == Decimal("50")


def test_human_review_rate_includes_approval_required():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.HUMAN_REVIEW,
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.RESOLVED_WITH_APPROVAL,
        ),
        make_decision(
            "CASE_003",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_004",
            DecisionOutcome.PENDING,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.human_review == 2
    assert metrics.human_review_rate == Decimal("50")


# ============================================================
# FINANCIAL VALUE
# ============================================================


def test_unresolved_financial_value_excludes_auto_resolved():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
            "1000",
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.PENDING,
            "200",
        ),
        make_decision(
            "CASE_003",
            DecisionOutcome.HUMAN_REVIEW,
            "300",
        ),
        make_decision(
            "CASE_004",
            DecisionOutcome.BLOCKED,
            "500",
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    assert (
        metrics.unresolved_financial_value
        == Decimal("1000")
    )


# ============================================================
# FALSE RESOLUTION
# ============================================================


def test_false_resolution_requires_ground_truth():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.false_resolutions == 0
    assert metrics.false_resolution_rate == Decimal("0")


def test_false_resolution_is_detected_against_ground_truth():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.AUTO_RESOLVED,
        ),
    ]

    ground_truth = {
        "CASE_001": DecisionOutcome.AUTO_RESOLVED,
        "CASE_002": DecisionOutcome.HUMAN_REVIEW,
    }

    metrics = calculate_decision_metrics(
        decisions,
        ground_truth=ground_truth,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.false_resolutions == 1
    assert metrics.false_resolution_rate == Decimal("50")


# ============================================================
# HUMAN AGREEMENT
# ============================================================


def test_human_agreement_is_none_without_human_data():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.human_agreements is None
    assert metrics.human_agreement_rate is None


def test_human_agreement_is_calculated():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.HUMAN_REVIEW,
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.BLOCKED,
        ),
        make_decision(
            "CASE_003",
            DecisionOutcome.AUTO_RESOLVED,
        ),
    ]

    human_reviews = {
        "CASE_001": DecisionOutcome.HUMAN_REVIEW,
        "CASE_002": DecisionOutcome.HUMAN_REVIEW,
        "CASE_003": DecisionOutcome.AUTO_RESOLVED,
    }

    metrics = calculate_decision_metrics(
        decisions,
        human_reviews=human_reviews,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.human_agreements == 2
    assert metrics.human_agreement_rate == (
        Decimal("200") / Decimal("3")
    )


# ============================================================
# INVESTIGATION REDUCTION
# ============================================================


def test_human_investigation_reduction_is_calculated():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_003",
            DecisionOutcome.HUMAN_REVIEW,
        ),
        make_decision(
            "CASE_004",
            DecisionOutcome.PENDING,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    assert metrics.human_investigation_reduction == (
        Decimal("75")
    )


# ============================================================
# THROUGHPUT
# ============================================================


def test_throughput_is_cases_per_second():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.AUTO_RESOLVED,
        ),
        make_decision(
            "CASE_003",
            DecisionOutcome.PENDING,
        ),
        make_decision(
            "CASE_004",
            DecisionOutcome.BLOCKED,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("1000"),
    )

    assert metrics.throughput == Decimal("4")


def test_non_positive_processing_time_produces_zero_throughput():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
        ),
    ]

    metrics = calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("0"),
    )

    assert metrics.throughput == Decimal("0")


# ============================================================
# IMMUTABILITY / OBSERVATIONAL BEHAVIOR
# ============================================================


def test_metrics_do_not_modify_decisions():
    decisions = [
        make_decision(
            "CASE_001",
            DecisionOutcome.AUTO_RESOLVED,
            "100",
        ),
        make_decision(
            "CASE_002",
            DecisionOutcome.HUMAN_REVIEW,
            "200",
        ),
    ]

    before = [
        (
            decision.case_id,
            decision.decision,
            decision.financial_impact,
        )
        for decision in decisions
    ]

    calculate_decision_metrics(
        decisions,
        processing_time_ms=Decimal("100"),
    )

    after = [
        (
            decision.case_id,
            decision.decision,
            decision.financial_impact,
        )
        for decision in decisions
    ]

    assert before == after