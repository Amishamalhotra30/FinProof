from decimal import Decimal

import pytest

from app.verification.materiality import (
    MaterialityEvaluator,
    evaluate_materiality,
)
from app.verification.models import Materiality


def test_zero_difference_is_not_material():
    evaluator = MaterialityEvaluator()

    assert (
        evaluator.evaluate(
            Decimal("0.00")
        )
        == Materiality.NONE
    )


def test_sub_rupee_difference_is_not_material():
    evaluator = MaterialityEvaluator()

    assert (
        evaluator.evaluate(
            Decimal("0.50")
        )
        == Materiality.NONE
    )


def test_low_difference_is_low_materiality():
    evaluator = MaterialityEvaluator()

    assert (
        evaluator.evaluate(
            Decimal("10.00")
        )
        == Materiality.LOW
    )


def test_medium_difference_is_medium_materiality():
    evaluator = MaterialityEvaluator()

    assert (
        evaluator.evaluate(
            Decimal("250.00")
        )
        == Materiality.MEDIUM
    )


def test_high_difference_is_high_materiality():
    evaluator = MaterialityEvaluator()

    assert (
        evaluator.evaluate(
            Decimal("1000.00")
        )
        == Materiality.HIGH
    )


def test_negative_difference_uses_absolute_value():
    evaluator = MaterialityEvaluator()

    assert (
        evaluator.evaluate(
            Decimal("-250.00")
        )
        == Materiality.MEDIUM
    )


def test_custom_thresholds_are_supported():
    evaluator = MaterialityEvaluator(
        low_threshold=Decimal("5.00"),
        medium_threshold=Decimal("50.00"),
        high_threshold=Decimal("500.00"),
    )

    assert (
        evaluator.evaluate(
            Decimal("4.99")
        )
        == Materiality.NONE
    )

    assert (
        evaluator.evaluate(
            Decimal("25.00")
        )
        == Materiality.LOW
    )

    assert (
        evaluator.evaluate(
            Decimal("100.00")
        )
        == Materiality.MEDIUM
    )

    assert (
        evaluator.evaluate(
            Decimal("500.00")
        )
        == Materiality.HIGH
    )


def test_invalid_threshold_order_is_rejected():
    with pytest.raises(ValueError):
        MaterialityEvaluator(
            low_threshold=Decimal("100.00"),
            medium_threshold=Decimal("10.00"),
            high_threshold=Decimal("1000.00"),
        )


def test_negative_threshold_is_rejected():
    with pytest.raises(ValueError):
        MaterialityEvaluator(
            low_threshold=Decimal("-1.00")
        )


def test_convenience_function_uses_default_evaluator():
    assert (
        evaluate_materiality(
            Decimal("250.00")
        )
        == Materiality.MEDIUM
    )