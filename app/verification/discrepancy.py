from decimal import Decimal

from app.verification.materiality import MaterialityEvaluator
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Discrepancy,
    Materiality,
)


class DiscrepancyBuilder:
    """
    Converts failed control checks into structured discrepancies.

    This component describes observable differences only.
    It does not infer root causes or investigate failures.

    Two categories of failures are supported:

    1. Numeric discrepancy
       The control provides expected and observed values.

    2. Structural discrepancy
       The control failed because evidence, ordering, or a
       relationship is missing/invalid. No meaningful monetary
       comparison exists in this case.
    """

    def __init__(
        self,
        materiality_evaluator: MaterialityEvaluator | None = None,
    ):
        self.materiality_evaluator = (
            materiality_evaluator
            or MaterialityEvaluator()
        )

    def build(
        self,
        control: ControlCheck,
    ) -> Discrepancy | None:
        """
        Build a discrepancy only when a control has failed.
        """

        if control.status != ControlStatus.FAIL:
            return None

        expected = control.expected_value
        observed = control.observed_value

        # ====================================================
        # NUMERIC FAILURE
        # ====================================================

        if (
            expected is not None
            and observed is not None
        ):
            difference = (
                control.difference
                if control.difference is not None
                else observed - expected
            )

            materiality = (
                self.materiality_evaluator.evaluate(
                    difference
                )
            )

            return Discrepancy(
                discrepancy_id=(
                    f"DISC_{control.control_id}"
                ),
                control_id=control.control_id,
                expected_value=expected,
                observed_value=observed,
                difference=difference,
                relative_difference=(
                    self._relative_difference(
                        expected,
                        difference,
                    )
                ),
                affected_event_ids=list(
                    control.affected_event_ids
                ),
                evidence_references=list(
                    control.supporting_evidence_ids
                ),
                materiality=materiality,
                blocking=control.blocking,
            )

        # ====================================================
        # STRUCTURAL FAILURE
        # ====================================================
        #
        # Structural controls such as EVENT_ORDERING do not
        # have a monetary expected/observed comparison.
        #
        # The Discrepancy model requires a Decimal difference
        # and a Materiality value, so we use the neutral
        # representations:
        #
        #     difference = 0
        #     materiality = NONE
        #
        # We do NOT invent a financial difference.
        # ====================================================

        return Discrepancy(
            discrepancy_id=(
                f"DISC_{control.control_id}"
            ),
            control_id=control.control_id,
            expected_value=None,
            observed_value=None,
            difference=Decimal("0"),
            relative_difference=None,
            affected_event_ids=list(
                control.affected_event_ids
            ),
            evidence_references=list(
                control.supporting_evidence_ids
            ),
            materiality=Materiality.NONE,
            blocking=control.blocking,
        )

    @staticmethod
    def _relative_difference(
        expected: Decimal,
        difference: Decimal,
    ) -> Decimal | None:
        if expected == Decimal("0"):
            return None

        return (
            abs(difference)
            / abs(expected)
        )


def build_discrepancy(
    control: ControlCheck,
) -> Discrepancy | None:
    """
    Convenience function for building one discrepancy.
    """

    return DiscrepancyBuilder().build(
        control
    )