from decimal import Decimal

from app.verification.evaluation import (
    VerificationEvaluation,
)


def _format_rate(
    value: Decimal,
) -> str:
    """
    Format a Decimal rate as a percentage with two decimals.
    """

    return f"{value * Decimal('100'):.2f}%"


def _format_decimal(
    value: Decimal,
) -> str:
    """
    Format a Decimal value with four decimal places.
    """

    return f"{value:.4f}"


def evaluation_to_dict(
    evaluation: VerificationEvaluation,
) -> dict:
    """
    Convert a VerificationEvaluation into a JSON-friendly
    dictionary.

    This does not modify the evaluation.
    """

    return {
        "total_cases": evaluation.total_cases,

        "control_precision": str(
            evaluation.control_precision
        ),

        "control_recall": str(
            evaluation.control_recall
        ),

        "false_pass_rate": str(
            evaluation.false_pass_rate
        ),

        "false_fail_rate": str(
            evaluation.false_fail_rate
        ),

        "pending_classification_accuracy": str(
            evaluation.pending_classification_accuracy
        ),

        "material_failure_detection_rate": str(
            evaluation.material_failure_detection_rate
        ),

        "financial_discrepancy_coverage": str(
            evaluation.financial_discrepancy_coverage
        ),

        "verification_throughput": str(
            evaluation.verification_throughput
        ),

        "actual_failures": (
            evaluation.actual_failures
        ),

        "detected_failures": (
            evaluation.detected_failures
        ),

        "actual_material_failures": (
            evaluation.actual_material_failures
        ),

        "detected_material_failures": (
            evaluation.detected_material_failures
        ),

        "actual_discrepancies": (
            evaluation.actual_discrepancies
        ),

        "detected_discrepancies": (
            evaluation.detected_discrepancies
        ),

        "pending_expected": (
            evaluation.pending_expected
        ),

        "pending_correct": (
            evaluation.pending_correct
        ),

        "processing_time_ms": str(
            evaluation.processing_time_ms
        ),

        "controls": [
            {
                "control_id": control.control_id,
                "true_positives": (
                    control.true_positives
                ),
                "true_negatives": (
                    control.true_negatives
                ),
                "false_positives": (
                    control.false_positives
                ),
                "false_negatives": (
                    control.false_negatives
                ),
                "precision": str(
                    control.precision
                ),
                "recall": str(
                    control.recall
                ),
                "false_pass_rate": str(
                    control.false_pass_rate
                ),
                "false_fail_rate": str(
                    control.false_fail_rate
                ),
            }
            for control in evaluation.controls
        ],
    }


def format_evaluation_report(
    evaluation: VerificationEvaluation,
) -> str:
    """
    Build a human-readable Phase 5 evaluation report.
    """

    lines = [
        "",
        "=" * 58,
        "FINPROOF VERIFICATION EVALUATION",
        "=" * 58,
        "",
        f"Cases evaluated              : "
        f"{evaluation.total_cases}",
        "",
        "OVERALL METRICS",
        "-" * 58,

        f"Control Precision            : "
        f"{_format_rate(evaluation.control_precision)}",

        f"Control Recall               : "
        f"{_format_rate(evaluation.control_recall)}",

        f"False-pass Rate              : "
        f"{_format_rate(evaluation.false_pass_rate)}",

        f"False-fail Rate              : "
        f"{_format_rate(evaluation.false_fail_rate)}",

        f"Pending Classification       : "
        f"{_format_rate(evaluation.pending_classification_accuracy)}",

        f"Material Failure Detection  : "
        f"{_format_rate(evaluation.material_failure_detection_rate)}",

        f"Financial Discrepancy Coverage: "
        f"{_format_rate(evaluation.financial_discrepancy_coverage)}",

        f"Verification Throughput      : "
        f"{_format_decimal(evaluation.verification_throughput)} "
        f"cases/sec",

        "",
        "COUNTS",
        "-" * 58,

        f"Actual failures              : "
        f"{evaluation.actual_failures}",

        f"Detected failures            : "
        f"{evaluation.detected_failures}",

        f"Actual material failures     : "
        f"{evaluation.actual_material_failures}",

        f"Detected material failures   : "
        f"{evaluation.detected_material_failures}",

        f"Actual discrepancies         : "
        f"{evaluation.actual_discrepancies}",

        f"Detected discrepancies       : "
        f"{evaluation.detected_discrepancies}",

        f"Expected pending controls    : "
        f"{evaluation.pending_expected}",

        f"Correct pending controls     : "
        f"{evaluation.pending_correct}",

        f"Processing time              : "
        f"{evaluation.processing_time_ms:.4f} ms",

        "",
        "CONTROL PERFORMANCE",
        "-" * 58,
    ]

    for control in evaluation.controls:
        lines.extend(
            [
                "",
                control.control_id,

                f"  Precision                  : "
                f"{_format_rate(control.precision)}",

                f"  Recall                     : "
                f"{_format_rate(control.recall)}",

                f"  False-pass Rate            : "
                f"{_format_rate(control.false_pass_rate)}",

                f"  False-fail Rate             : "
                f"{_format_rate(control.false_fail_rate)}",

                f"  TP                         : "
                f"{control.true_positives}",

                f"  TN                         : "
                f"{control.true_negatives}",

                f"  FP                         : "
                f"{control.false_positives}",

                f"  FN                         : "
                f"{control.false_negatives}",
            ]
        )

    lines.extend(
        [
            "",
            "=" * 58,
        ]
    )

    return "\n".join(lines)


def print_evaluation_report(
    evaluation: VerificationEvaluation,
) -> None:
    """
    Print the complete Phase 5 evaluation report.
    """

    print(
        format_evaluation_report(
            evaluation
        )
    )