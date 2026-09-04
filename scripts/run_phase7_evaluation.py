from __future__ import annotations

from decimal import Decimal
from time import perf_counter

from app.decisions.metrics import (
    DecisionMetricsCalculator,
)
from app.decisions.models import (
    DecisionOutcome,
    DecisionPolicy,
    DecisionResult,
    MaterialityLevel,
)
from app.decisions.service import (
    DecisionService,
)
from app.investigation.models import (
    InvestigationResult,
    InvestigationStatus,
)
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Discrepancy,
    Materiality,
    Severity,
    VerificationResult,
    VerificationStatus,
)


# ============================================================
# BENCHMARK FIXTURES
# ============================================================


def _passed_case(case_id: str) -> VerificationResult:
    return VerificationResult(
        case_id=case_id,
        status=VerificationStatus.VERIFIED,
        expected_state={},
        controls=[
            ControlCheck(
                control_id="CONTROL",
                control_name="Benchmark control",
                status=ControlStatus.PASS,
                severity=Severity.INFO,
                blocking=False,
            )
        ],
        discrepancies=[],
    )


def _pending_case(case_id: str) -> VerificationResult:
    return VerificationResult(
        case_id=case_id,
        status=VerificationStatus.PENDING,
        expected_state={},
        controls=[
            ControlCheck(
                control_id="CONTROL",
                control_name="Benchmark control",
                status=ControlStatus.PENDING,
                severity=Severity.INFO,
                blocking=False,
            )
        ],
        discrepancies=[],
    )


def _failed_case(
    case_id: str,
    *,
    amount: Decimal,
    materiality: Materiality,
    blocking: bool = False,
) -> VerificationResult:
    discrepancy_id = f"{case_id}-DISC"

    discrepancy = Discrepancy(
        discrepancy_id=discrepancy_id,
        control_id="SETTLEMENT_AMOUNT",
        expected_value=amount,
        observed_value=Decimal("0"),
        difference=amount,
        affected_event_ids=["EVENT_001"],
        evidence_references=["EVENT_001"],
        materiality=materiality,
        blocking=blocking,
    )

    return VerificationResult(
        case_id=case_id,
        status=VerificationStatus.FAILED,
        expected_state={},
        controls=[
            ControlCheck(
                control_id="SETTLEMENT_AMOUNT",
                control_name="Settlement amount",
                status=ControlStatus.FAIL,
                expected_value=amount,
                observed_value=Decimal("0"),
                difference=amount,
                affected_event_ids=["EVENT_001"],
                supporting_evidence_ids=["EVENT_001"],
                severity=Severity.MEDIUM,
                blocking=blocking,
            )
        ],
        discrepancies=[discrepancy],
    )


def _resolved_investigation(
    case_id: str,
    discrepancy_id: str,
    amount: Decimal,
) -> InvestigationResult:
    return InvestigationResult(
        investigation_id=f"{case_id}-INV",
        case_id=case_id,
        discrepancy_id=discrepancy_id,
        status=InvestigationStatus.RESOLVED,
        hypotheses=[],
        explained_amount=amount,
        remaining_unexplained=Decimal("0"),
        supporting_evidence_ids=["EVENT_001"],
        conclusion="Discrepancy fully explained by validated evidence.",
        validated=True,
    )


def _insufficient_investigation(
    case_id: str,
    discrepancy_id: str,
    amount: Decimal,
) -> InvestigationResult:
    return InvestigationResult(
        investigation_id=f"{case_id}-INV",
        case_id=case_id,
        discrepancy_id=discrepancy_id,
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        hypotheses=[],
        explained_amount=Decimal("0"),
        remaining_unexplained=amount,
        supporting_evidence_ids=[],
        conclusion="Required evidence is unavailable.",
        validated=True,
    )


def _unresolved_investigation(
    case_id: str,
    discrepancy_id: str,
    amount: Decimal,
) -> InvestigationResult:
    return InvestigationResult(
        investigation_id=f"{case_id}-INV",
        case_id=case_id,
        discrepancy_id=discrepancy_id,
        status=InvestigationStatus.UNRESOLVED,
        hypotheses=[],
        explained_amount=Decimal("0"),
        remaining_unexplained=amount,
        supporting_evidence_ids=[],
        conclusion="Available evidence does not fully explain discrepancy.",
        validated=True,
    )


def _build_benchmark_cases() -> list[
    tuple[
        VerificationResult,
        InvestigationResult | None,
        DecisionOutcome,
    ]
]:
    cases = []

    # --------------------------------------------------------
    # 1-50: routine clean cases
    # --------------------------------------------------------

    for index in range(1, 51):
        case_id = f"P7-BENCH-{index:04d}"

        cases.append(
            (
                _passed_case(case_id),
                None,
                DecisionOutcome.AUTO_RESOLVED,
            )
        )

    # --------------------------------------------------------
    # 51-60: expected events pending
    # --------------------------------------------------------

    for index in range(51, 61):
        case_id = f"P7-BENCH-{index:04d}"

        cases.append(
            (
                _pending_case(case_id),
                None,
                DecisionOutcome.PENDING,
            )
        )

    # --------------------------------------------------------
    # 61-70: fully explained non-material
    # --------------------------------------------------------

    for index in range(61, 71):
        case_id = f"P7-BENCH-{index:04d}"

        verification = _failed_case(
            case_id,
            amount=Decimal("500"),
            materiality=Materiality.LOW,
        )

        investigation = _resolved_investigation(
            case_id,
            f"{case_id}-DISC",
            Decimal("500"),
        )

        cases.append(
            (
                verification,
                investigation,
                DecisionOutcome.AUTO_RESOLVED,
            )
        )

    # --------------------------------------------------------
    # 71-80: fully explained material
    # --------------------------------------------------------

    for index in range(71, 81):
        case_id = f"P7-BENCH-{index:04d}"

        verification = _failed_case(
            case_id,
            amount=Decimal("5000"),
            materiality=Materiality.HIGH,
        )

        investigation = _resolved_investigation(
            case_id,
            f"{case_id}-DISC",
            Decimal("5000"),
        )

        cases.append(
            (
                verification,
                investigation,
                DecisionOutcome.RESOLVED_WITH_APPROVAL,
            )
        )

    # --------------------------------------------------------
    # 81-90: insufficient evidence
    # --------------------------------------------------------

    for index in range(81, 91):
        case_id = f"P7-BENCH-{index:04d}"

        verification = _failed_case(
            case_id,
            amount=Decimal("2000"),
            materiality=Materiality.MEDIUM,
        )

        investigation = _insufficient_investigation(
            case_id,
            f"{case_id}-DISC",
            Decimal("2000"),
        )

        cases.append(
            (
                verification,
                investigation,
                DecisionOutcome.HUMAN_REVIEW,
            )
        )

    # --------------------------------------------------------
    # 91-95: unresolved + high materiality + blocking
    # --------------------------------------------------------

    for index in range(91, 96):
        case_id = f"P7-BENCH-{index:04d}"

        verification = _failed_case(
            case_id,
            amount=Decimal("10000"),
            materiality=Materiality.HIGH,
            blocking=True,
        )

        investigation = _unresolved_investigation(
            case_id,
            f"{case_id}-DISC",
            Decimal("10000"),
        )

        cases.append(
            (
                verification,
                investigation,
                DecisionOutcome.BLOCKED,
            )
        )

    # --------------------------------------------------------
    # 96-100: unresolved + low materiality
    # --------------------------------------------------------

    for index in range(96, 101):
        case_id = f"P7-BENCH-{index:04d}"

        verification = _failed_case(
            case_id,
            amount=Decimal("750"),
            materiality=Materiality.LOW,
        )

        investigation = _unresolved_investigation(
            case_id,
            f"{case_id}-DISC",
            Decimal("750"),
        )

        cases.append(
            (
                verification,
                investigation,
                DecisionOutcome.HUMAN_REVIEW,
            )
        )

    return cases


# ============================================================
# EVALUATION
# ============================================================


def run_evaluation() -> None:
    benchmark_cases = _build_benchmark_cases()

    policy = DecisionPolicy(
        auto_resolution_threshold=Decimal("1000")
    )

    service = DecisionService(
        policy=policy
    )

    decisions: list[DecisionResult] = []
    ground_truth: dict[
        str,
        DecisionOutcome,
    ] = {}

    started = perf_counter()

    for verification, investigation, expected in benchmark_cases:
        result = service.decide(
            verification,
            investigation,
        )

        decisions.append(
            result.decision
        )

        ground_truth[
            verification.case_id
        ] = expected

    elapsed_ms = Decimal(
        str(
            (perf_counter() - started) * 1000
        )
    )

    metrics = DecisionMetricsCalculator().calculate(
        decisions,
        ground_truth=ground_truth,
        processing_time_ms=elapsed_ms,
    )

    # --------------------------------------------------------
    # Hard correctness checks
    # --------------------------------------------------------

    mismatches = [
        (
            decision.case_id,
            decision.decision,
            ground_truth[decision.case_id],
        )
        for decision in decisions
        if decision.decision
        != ground_truth[decision.case_id]
    ]

    print("=" * 60)
    print("FINPROOF — PHASE 7 DECISION EVALUATION")
    print("=" * 60)

    print()
    print(
        f"Total cases                 : "
        f"{metrics.total_cases}"
    )
    print(
        f"AUTO_RESOLVED               : "
        f"{metrics.auto_resolved}"
    )
    print(
        f"PENDING                     : "
        f"{metrics.pending}"
    )
    print(
        f"HUMAN_REVIEW                : "
        f"{metrics.human_review}"
    )
    print(
        f"BLOCKED                     : "
        f"{metrics.blocked}"
    )

    print()
    print(
        f"Automation rate             : "
        f"{metrics.automation_rate:.2f}%"
    )
    print(
        f"Human review rate           : "
        f"{metrics.human_review_rate:.2f}%"
    )
    print(
        f"False resolution rate       : "
        f"{metrics.false_resolution_rate:.2f}%"
    )
    print(
        f"Human investigation reduction: "
        f"{metrics.human_investigation_reduction:.2f}%"
    )

    print()
    print(
        f"Unresolved financial value  : "
        f"₹{metrics.unresolved_financial_value}"
    )
    print(
        f"Processing time             : "
        f"{metrics.processing_time_ms:.4f} ms"
    )
    print(
        f"Throughput                  : "
        f"{metrics.throughput:.2f} cases/sec"
    )

    print()
    print(
        f"Decision mismatches         : "
        f"{len(mismatches)}"
    )

    print()

    if mismatches:
        print("MISMATCHES:")

        for case_id, actual, expected in mismatches:
            print(
                f"  {case_id}: "
                f"actual={actual.value}, "
                f"expected={expected.value}"
            )

    print("=" * 60)

    if mismatches:
        raise RuntimeError(
            "Phase 7 benchmark contains decision mismatches."
        )


if __name__ == "__main__":
    run_evaluation()