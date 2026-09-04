from decimal import Decimal

from app.evaluation.failure_analysis import (
    FailureAnalyzer,
    FailureCategory,
    FailureRecord,
    FailureType,
)


def _failure(
    case_id: str,
    failure_type: FailureType,
    value: str,
):
    return FailureRecord(
        case_id=case_id,
        category=FailureCategory.SAFETY,
        failure_type=failure_type,
        financial_value=Decimal(value),
        description="Synthetic evaluation failure",
    )


def test_empty_failure_set():
    summary = FailureAnalyzer().analyze([])

    assert summary.total_failures == 0
    assert summary.total_financial_value == Decimal("0")
    assert summary.false_passes == 0
    assert summary.false_resolutions == 0


def test_failure_counts_are_classified():
    failures = [
        _failure(
            "CASE-1",
            FailureType.FALSE_PASS,
            "100",
        ),
        _failure(
            "CASE-2",
            FailureType.FALSE_FAIL,
            "200",
        ),
        _failure(
            "CASE-3",
            FailureType.FALSE_EXPLANATION,
            "300",
        ),
        _failure(
            "CASE-4",
            FailureType.FALSE_RESOLUTION,
            "400",
        ),
        _failure(
            "CASE-5",
            FailureType.FALSE_BLOCK,
            "500",
        ),
    ]

    summary = FailureAnalyzer().analyze(
        failures
    )

    assert summary.total_failures == 5
    assert (
        summary.total_financial_value
        == Decimal("1500")
    )

    assert summary.false_passes == 1
    assert summary.false_fails == 1
    assert summary.false_explanations == 1
    assert summary.false_resolutions == 1
    assert summary.false_blocks == 1


def test_financial_values_are_aggregated():
    failures = [
        _failure(
            "CASE-1",
            FailureType.FALSE_PASS,
            "1000",
        ),
        _failure(
            "CASE-2",
            FailureType.FALSE_PASS,
            "2500",
        ),
    ]

    summary = FailureAnalyzer().analyze(
        failures
    )

    assert (
        summary.false_pass_value
        == Decimal("3500")
    )

    assert (
        summary.total_financial_value
        == Decimal("3500")
    )


def test_value_weighted_rate():
    failures = [
        _failure(
            "CASE-1",
            FailureType.FALSE_PASS,
            "250",
        ),
        _failure(
            "CASE-2",
            FailureType.FALSE_FAIL,
            "750",
        ),
    ]

    summary = FailureAnalyzer().analyze(
        failures
    )

    assert (
        summary.false_pass_value_rate
        == Decimal("0.25")
    )


def test_false_explanation_value_rate():
    failures = [
        _failure(
            "CASE-1",
            FailureType.FALSE_EXPLANATION,
            "100",
        ),
        _failure(
            "CASE-2",
            FailureType.FALSE_FAIL,
            "900",
        ),
    ]

    summary = FailureAnalyzer().analyze(
        failures
    )

    assert (
        summary.false_explanation_value_rate
        == Decimal("0.1")
    )


def test_false_resolution_value_rate():
    failures = [
        _failure(
            "CASE-1",
            FailureType.FALSE_RESOLUTION,
            "500",
        ),
        _failure(
            "CASE-2",
            FailureType.FALSE_FAIL,
            "500",
        ),
    ]

    summary = FailureAnalyzer().analyze(
        failures
    )

    assert (
        summary.false_resolution_value_rate
        == Decimal("0.5")
    )


def test_safe_degradation_failures_are_tracked():
    failures = [
        _failure(
            "CASE-1",
            FailureType.SAFE_DEGRADATION_FAILURE,
            "1000",
        ),
    ]

    summary = FailureAnalyzer().analyze(
        failures
    )

    assert (
        summary.safe_degradation_failures
        == 1
    )

    assert (
        summary.safe_degradation_failure_value
        == Decimal("1000")
    )