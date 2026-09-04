from decimal import Decimal

from app.verification.models import Materiality


class MaterialityEvaluator:
    """
    Determines the materiality of a financial difference.

    Materiality is based only on deterministic monetary thresholds.
    It does not determine the cause of a discrepancy.
    """

    def __init__(
        self,
        low_threshold: Decimal = Decimal("1.00"),
        medium_threshold: Decimal = Decimal("100.00"),
        high_threshold: Decimal = Decimal("1000.00"),
    ):
        if (
            low_threshold < Decimal("0")
            or medium_threshold < low_threshold
            or high_threshold < medium_threshold
        ):
            raise ValueError(
                "Materiality thresholds must be non-negative "
                "and ordered from low to high"
            )

        self.low_threshold = low_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold

    def evaluate(
        self,
        difference: Decimal,
    ) -> Materiality:
        """
        Classify an absolute monetary difference.
        """

        absolute_difference = abs(difference)

        if absolute_difference == Decimal("0"):
            return Materiality.NONE

        if absolute_difference < self.low_threshold:
            return Materiality.NONE

        if absolute_difference < self.medium_threshold:
            return Materiality.LOW

        if absolute_difference < self.high_threshold:
            return Materiality.MEDIUM

        return Materiality.HIGH


def evaluate_materiality(
    difference: Decimal,
) -> Materiality:
    """
    Convenience function using the default thresholds.
    """

    return MaterialityEvaluator().evaluate(
        difference
    )