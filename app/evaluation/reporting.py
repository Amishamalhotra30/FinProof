from __future__ import annotations

from app.evaluation.report import Phase8Report


def print_phase8_report(
    report: Phase8Report,
) -> None:
    print()
    print("=" * 70)
    print("FINPROOF — PHASE 8 EVALUATION REPORT")
    print("=" * 70)

    print()
    print("CONFIGURATION")
    print("-" * 70)
    print(
        f"Benchmark cases : "
        f"{report.benchmark_cases}"
    )

    print()
    print("VERIFICATION")
    print("-" * 70)
    print(
        f"Cases                       : "
        f"{report.verification_cases}"
    )
    print(
        f"False-pass rate             : "
        f"{report.verification_false_pass_rate:.2%}"
    )
    print(
        f"False-fail rate             : "
        f"{report.verification_false_fail_rate:.2%}"
    )
    print(
        f"Material failure detection  : "
        f"{report.verification_material_detection_rate:.2%}"
    )
    print(
        f"Discrepancy coverage        : "
        f"{report.verification_discrepancy_coverage:.2%}"
    )
    print(
        f"Throughput                  : "
        f"{report.verification_throughput:.2f} cases/sec"
    )

    print()
    print("INVESTIGATION")
    print("-" * 70)
    print(
        f"Cases                       : "
        f"{report.investigation_cases}"
    )
    print(
        f"Investigation coverage      : "
        f"{report.investigation_coverage:.2%}"
    )
    print(
        f"Full explanation rate       : "
        f"{report.investigation_full_explanation_rate:.2%}"
    )
    print(
        f"False explanation rate      : "
        f"{report.investigation_false_explanation_rate:.2%}"
    )
    print(
        f"Explanation coverage        : "
        f"{report.investigation_explanation_coverage:.2%}"
    )
    print(
        f"Throughput                  : "
        f"{report.investigation_throughput:.2f} cases/sec"
    )

    print()
    print("DECISION")
    print("-" * 70)
    print(
        f"Cases                       : "
        f"{report.decision_cases}"
    )
    print(
        f"Automation rate             : "
        f"{report.decision_automation_rate:.2f}%"
    )
    print(
        f"Human review rate           : "
        f"{report.decision_human_review_rate:.2f}%"
    )
    print(
        f"False resolution rate       : "
        f"{report.decision_false_resolution_rate:.2f}%"
    )
    print(
        f"Throughput                  : "
        f"{report.decision_throughput:.2f} cases/sec"
    )

    print()
    print("SAFETY")
    print("-" * 70)
    print(
        f"Safety status               : "
        f"{report.safety_status}"
    )
    print(
        f"Overall status              : "
        f"{report.overall_status}"
    )

    print()
    print("=" * 70)
    print("PHASE 8 EVALUATION COMPLETE")
    print("=" * 70)