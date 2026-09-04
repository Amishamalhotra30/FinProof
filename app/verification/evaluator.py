from dataclasses import dataclass
from decimal import Decimal

from app.verification.evaluation import (
    ControlEvaluation,
    VerificationEvaluation,
)
from app.verification.models import (
    ControlStatus,
    Materiality,
    VerificationResult,
    VerificationStatus,
)


@dataclass(frozen=True)
class GroundTruthVerification:
    """
    Evaluation-only description of what should have happened.

    This must never be supplied to the runtime verifier.
    """

    failed_controls: frozenset[str] = frozenset()

    material_failed_controls: frozenset[str] = (
        frozenset()
    )

    discrepancy_controls: frozenset[str] = (
        frozenset()
    )

    pending_controls: frozenset[str] = (
        frozenset()
    )


class VerificationEvaluator:
    """
    Evaluates Phase 5 verification results against ground truth.

    This class is deliberately separated from FinancialStateVerifier.
    """

    def evaluate(
        self,
        results: list[VerificationResult],
        ground_truth: list[GroundTruthVerification],
    ) -> VerificationEvaluation:

        if len(results) != len(ground_truth):
            raise ValueError(
                "results and ground_truth must contain "
                "the same number of cases"
            )

        control_ids: set[str] = set()

        for result in results:
            control_ids.update(
                control.control_id
                for control in result.controls
            )

        evaluations: list[ControlEvaluation] = []

        for control_id in sorted(control_ids):

            tp = 0
            tn = 0
            fp = 0
            fn = 0

            for result, expected in zip(
                results,
                ground_truth,
            ):
                actual_failed = (
                    control_id
                    in expected.failed_controls
                )

                observed_control = next(
                    (
                        control
                        for control
                        in result.controls
                        if control.control_id
                        == control_id
                    ),
                    None,
                )

                observed_failed = (
                    observed_control is not None
                    and observed_control.status
                    == ControlStatus.FAIL
                )

                if (
                    observed_failed
                    and actual_failed
                ):
                    tp += 1

                elif (
                    not observed_failed
                    and not actual_failed
                ):
                    tn += 1

                elif observed_failed:
                    fp += 1

                else:
                    fn += 1

            evaluations.append(
                ControlEvaluation(
                    control_id=control_id,
                    true_positives=tp,
                    true_negatives=tn,
                    false_positives=fp,
                    false_negatives=fn,
                )
            )

        actual_failures = sum(
            bool(expected.failed_controls)
            for expected in ground_truth
        )

        detected_failures = sum(
            result.status
            == VerificationStatus.FAILED
            for result in results
        )

        actual_material_failures = sum(
            bool(
                expected.material_failed_controls
            )
            for expected in ground_truth
        )

        detected_material_failures = 0

        for result, expected in zip(
            results,
            ground_truth,
        ):
            detected_controls = {
                control.control_id
                for control in result.controls
                if (
                    control.status
                    == ControlStatus.FAIL
                    and control.control_id
                    in expected.material_failed_controls
                )
            }

            if detected_controls:
                detected_material_failures += 1

        actual_discrepancies = sum(
            len(expected.discrepancy_controls)
            for expected in ground_truth
        )

        detected_discrepancies = 0

        for result, expected in zip(
            results,
            ground_truth,
        ):
            detected_discrepancies += sum(
                discrepancy.control_id
                in expected.discrepancy_controls
                for discrepancy
                in result.discrepancies
            )

        pending_expected = sum(
            len(expected.pending_controls)
            for expected in ground_truth
        )

        pending_correct = 0

        for result, expected in zip(
            results,
            ground_truth,
        ):
            observed_pending = {
                control.control_id
                for control in result.controls
                if control.status
                == ControlStatus.PENDING
            }

            pending_correct += len(
                observed_pending
                & expected.pending_controls
            )

        processing_time_ms = sum(
            (
                result.processing_time_ms
                or Decimal("0")
            )
            for result in results
        )

        return VerificationEvaluation(
            controls=tuple(evaluations),
            total_cases=len(results),
            actual_failures=actual_failures,
            detected_failures=detected_failures,
            actual_material_failures=(
                actual_material_failures
            ),
            detected_material_failures=(
                detected_material_failures
            ),
            actual_discrepancies=(
                actual_discrepancies
            ),
            detected_discrepancies=(
                detected_discrepancies
            ),
            pending_expected=pending_expected,
            pending_correct=pending_correct,
            processing_time_ms=processing_time_ms,
        )


def evaluate_verification(
    results: list[VerificationResult],
    ground_truth: list[GroundTruthVerification],
) -> VerificationEvaluation:
    """
    Convenience function for evaluating verification results.
    """

    return VerificationEvaluator().evaluate(
        results,
        ground_truth,
    )