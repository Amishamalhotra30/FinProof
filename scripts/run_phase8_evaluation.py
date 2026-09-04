from __future__ import annotations

from decimal import Decimal

from app.evaluation.final_runner import (
    run_phase8_final,
)


NUM_CASES = 100
SEED = 42


def _rate_fraction(value) -> str:
    """
    Format a fractional metric such as 0.85 as 85.00%.
    Used by Phase 5 and Phase 6.
    """
    return f"{float(value) * 100:.2f}%"


def _print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def print_phase8_report(report) -> None:

    # =========================================================
    # HEADER
    # =========================================================

    print()
    print("=" * 72)
    print("FINPROOF — PHASE 8 FINAL EVALUATION")
    print("=" * 72)

    print()
    print("CONFIGURATION")
    print("-" * 72)
    print(f"Benchmark cases             : {NUM_CASES}")
    print(f"Seed                        : {SEED}")

    # =========================================================
    # DATASET SCOPE
    # =========================================================

    print()
    print("DATASET SCOPE")
    print("-" * 72)

    print(
        "Phase 5, Phase 6 and Phase 7 retain their "
        "existing phase-specific benchmark datasets."
    )

    print(
        "This report aggregates phase-level evaluation "
        "results and does not claim same-case end-to-end accuracy."
    )

    # =========================================================
    # PHASE 5
    # =========================================================

    _print_section(
        "PHASE 5 — VERIFICATION EVALUATION"
    )

    verification = report.verification

    print(
        f"Cases evaluated             : "
        f"{verification.total_cases}"
    )

    print(
        f"Actual failures             : "
        f"{verification.actual_failures}"
    )

    print(
        f"Detected failures           : "
        f"{verification.detected_failures}"
    )

    print(
        f"False-pass rate             : "
        f"{_rate_fraction(verification.false_pass_rate)}"
    )

    print(
        f"False-fail rate             : "
        f"{_rate_fraction(verification.false_fail_rate)}"
    )

    print(
        f"Material failure detection  : "
        f"{_rate_fraction(verification.material_failure_detection_rate)}"
    )

    print(
        f"Discrepancy coverage        : "
        f"{_rate_fraction(verification.financial_discrepancy_coverage)}"
    )

    print(
        f"Pending classification      : "
        f"{_rate_fraction(verification.pending_classification_accuracy)}"
    )

    print(
        f"Processing time             : "
        f"{verification.processing_time_ms:.4f} ms"
    )

    print(
        f"Throughput                  : "
        f"{verification.verification_throughput:.2f} cases/sec"
    )

    # =========================================================
    # PHASE 6
    # =========================================================

    _print_section(
        "PHASE 6 — INVESTIGATION EVALUATION"
    )

    investigation = report.investigation

    print(
        f"Total cases                 : "
        f"{investigation.total_cases}"
    )

    print(
        f"Corrupted cases             : "
        f"{investigation.corrupted_cases}"
    )

    print(
        f"Investigated cases          : "
        f"{investigation.investigated_cases}"
    )

    print(
        f"Investigation coverage      : "
        f"{_rate_fraction(investigation.investigation_coverage)}"
    )

    print()
    print("INVESTIGATION OUTCOMES")
    print("-" * 72)

    print(
        f"Fully explained             : "
        f"{investigation.fully_explained_cases}"
    )

    print(
        f"Partially explained         : "
        f"{investigation.partially_explained_cases}"
    )

    print(
        f"Unresolved                  : "
        f"{investigation.unresolved_cases}"
    )

    print(
        f"Insufficient evidence       : "
        f"{investigation.insufficient_evidence_cases}"
    )

    print(
        f"Contradictions              : "
        f"{investigation.contradiction_cases}"
    )

    print()
    print("INVESTIGATION QUALITY")
    print("-" * 72)

    print(
        f"Full explanation rate       : "
        f"{_rate_fraction(investigation.full_explanation_rate)}"
    )

    print(
        f"Partial explanation rate    : "
        f"{_rate_fraction(investigation.partial_explanation_rate)}"
    )

    print(
        f"Unresolved rate             : "
        f"{_rate_fraction(investigation.unresolved_rate)}"
    )

    print(
        f"Contradiction rate          : "
        f"{_rate_fraction(investigation.contradiction_rate)}"
    )

    print(
        f"Validation rate             : "
        f"{_rate_fraction(investigation.validation_rate)}"
    )

    print(
        f"Hypothesis alignment rate   : "
        f"{_rate_fraction(investigation.hypothesis_alignment_rate)}"
    )

    print(
        f"False explanation rate      : "
        f"{_rate_fraction(investigation.false_explanation_rate)}"
    )

    print(
        f"Explanation coverage        : "
        f"{_rate_fraction(investigation.explanation_coverage)}"
    )

    print()
    print("FINANCIAL EXPLANATION")
    print("-" * 72)

    print(
        f"Total discrepancy amount    : "
        f"{investigation.total_discrepancy_amount}"
    )

    print(
        f"Total explained amount      : "
        f"{investigation.total_explained_amount}"
    )

    print(
        f"Total remaining amount      : "
        f"{investigation.total_remaining_amount}"
    )

    print(
        f"Supporting evidence items   : "
        f"{investigation.supporting_evidence_count}"
    )

    print()
    print(
        f"Processing time             : "
        f"{investigation.processing_time_ms} ms"
    )

    print(
        f"Investigation throughput    : "
        f"{investigation.throughput:.2f} cases/sec"
    )

    # =========================================================
    # PHASE 7
    # =========================================================

    _print_section(
        "PHASE 7 — DECISION EVALUATION"
    )

    decision = report.decision

    print(
        f"Total cases                 : "
        f"{decision.total_cases}"
    )

    print(
        f"AUTO_RESOLVED               : "
        f"{decision.auto_resolved}"
    )

    print(
        f"PENDING                     : "
        f"{decision.pending}"
    )

    print(
        f"HUMAN_REVIEW                : "
        f"{decision.human_review}"
    )

    print(
        f"BLOCKED                     : "
        f"{decision.blocked}"
    )

    print()
    print(
        f"Automation rate             : "
        f"{decision.automation_rate:.2f}%"
    )

    print(
        f"Human review rate           : "
        f"{decision.human_review_rate:.2f}%"
    )

    print(
        f"False resolution rate       : "
        f"{decision.false_resolution_rate:.2f}%"
    )

    print(
        f"Human investigation reduction: "
        f"{decision.human_investigation_reduction:.2f}%"
    )

    print(
        f"Unresolved financial value  : "
        f"₹{decision.unresolved_financial_value}"
    )

    print(
        f"Processing time             : "
        f"{decision.processing_time_ms:.4f} ms"
    )

    print(
        f"Throughput                  : "
        f"{decision.throughput:.2f} cases/sec"
    )

    # =========================================================
    # ADVERSARIAL
    # =========================================================

    _print_section(
        "PHASE 8 — ADVERSARIAL SAFETY"
    )

    print(
        f"Adversarial cases           : "
        f"{report.adversarial_total}"
    )

    print(
        f"Safe cases                  : "
        f"{report.adversarial_safe}"
    )

    print(
        f"Adversarial safety rate     : "
        f"{_rate_fraction(report.adversarial_safety_rate)}"
    )

    print()

    for result in report.adversarial_results:

        print(
            f"{result.case_id:<28}"
            f"{result.scenario:<32}"
            f"status={str(result.status):<24}"
            f"safe={result.safe}"
        )

    # =========================================================
    # PERFORMANCE
    # =========================================================

    _print_section(
        "PHASE 8 — PERFORMANCE BENCHMARK"
    )

    print(
        f"{'Cases':>8}"
        f"{'Records':>10}"
        f"{'Generation(s)':>16}"
        f"{'Reconciliation(s)':>20}"
        f"{'Cases/sec':>16}"
    )

    print("-" * 72)

    for measurement in (
        report.performance.measurements
    ):

        print(
            f"{measurement.cases:>8}"
            f"{measurement.records:>10}"
            f"{measurement.generation_seconds:>16.6f}"
            f"{measurement.reconciliation_seconds:>20.6f}"
            f"{measurement.reconciliation_cases_per_second:>16.2f}"
        )

    print()

    print(
        f"Largest workload             : "
        f"{report.performance.largest_case_count:,} cases"
    )

    print(
        f"Minimum reconciliation      : "
        f"{report.performance.minimum_reconciliation_throughput:.2f} "
        f"cases/sec"
    )

    print()
    print(
        "Scope: deterministic benchmark generation + reconciliation."
    )

    print(
        "This is not an end-to-end application throughput claim."
    )

    # =========================================================
    # FAILURE ANALYSIS
    # =========================================================

    _print_section(
        "PHASE 8 — FAILURE ANALYSIS"
    )

    analysis = report.failure_analysis

    print(
        f"Total failures              : "
        f"{analysis.total_failures}"
    )

    print(
        f"Total financial value       : "
        f"₹{analysis.total_financial_value}"
    )

    print(
        f"False-pass value            : "
        f"₹{analysis.false_pass_value}"
    )

    print(
        f"False-fail value            : "
        f"₹{analysis.false_fail_value}"
    )

    print(
        f"False-explanation value     : "
        f"₹{analysis.false_explanation_value}"
    )

    print(
        f"False-resolution value      : "
        f"₹{analysis.false_resolution_value}"
    )

    print(
        f"Safe-degradation failures   : "
        f"{analysis.safe_degradation_failures}"
    )

    print(
        f"Safe-degradation value      : "
        f"₹{analysis.safe_degradation_failure_value}"
    )

    # =========================================================
    # FINAL VERDICT
    # =========================================================

    _print_section(
        "FINAL PHASE 8 VERDICT"
    )

    print(
        f"Safety status               : "
        f"{report.safety_status}"
    )

    if report.safety_status == "SAFE":
        print(
            "No false-pass, false-explanation, false-resolution, "
            "or adversarial safety failures were observed."
        )
    else:
        print(
            "One or more safety conditions require review."
        )

    print()
    print("=" * 72)
    print("PHASE 8 EVALUATION COMPLETE")
    print("=" * 72)


def main() -> None:

    report = run_phase8_final(
        num_cases=NUM_CASES,
        seed=SEED,
    )

    print_phase8_report(report)


if __name__ == "__main__":
    main()