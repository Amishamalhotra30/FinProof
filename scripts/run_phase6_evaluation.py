from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter

from app.benchmark import generate_benchmark
from app.corruption.models import CorruptionType

from app.investigation.case_builder import (
    InvestigationCaseBuilder,
)

from app.investigation.models import (
    HypothesisStatus,
    HypothesisType,
    InvestigationResult,
    InvestigationStatus,
)

from app.investigation.service import (
    InvestigationService,
)

from app.investigation.validator import (
    InvestigationResultValidator,
)


NUM_CASES = 100
SEED = 42


# ============================================================
# PHASE 6 EVALUATION RESULT
# ============================================================


@dataclass(frozen=True)
class Phase6Evaluation:
    """
    Evaluation-only aggregate for Phase 6 investigation.

    This object belongs to the benchmark/evaluation layer.
    It is not used by the runtime investigation engine.
    """

    total_cases: int = 0
    corrupted_cases: int = 0
    investigated_cases: int = 0
    investigated_discrepancies: int = 0

    fully_explained_cases: int = 0
    partially_explained_cases: int = 0

    unresolved_cases: int = 0
    insufficient_evidence_cases: int = 0
    contradiction_cases: int = 0

    validated_cases: int = 0

    hypothesis_aligned_cases: int = 0
    false_explanation_cases: int = 0

    total_explained_amount: Decimal = Decimal("0")
    total_discrepancy_amount: Decimal = Decimal("0")
    total_remaining_amount: Decimal = Decimal("0")

    supporting_evidence_count: int = 0

    processing_time_ms: Decimal = Decimal("0")

    @property
    def investigation_coverage(self) -> float:
        if self.corrupted_cases == 0:
            return 1.0

        return (
            self.investigated_cases
            / self.corrupted_cases
        )

    @property
    def full_explanation_rate(self) -> float:
        if self.investigated_cases == 0:
            return 0.0

        return (
            self.fully_explained_cases
            / self.investigated_cases
        )

    @property
    def partial_explanation_rate(self) -> float:
        if self.investigated_cases == 0:
            return 0.0

        return (
            self.partially_explained_cases
            / self.investigated_cases
        )

    @property
    def unresolved_rate(self) -> float:
        if self.investigated_cases == 0:
            return 0.0

        return (
            self.unresolved_cases
            / self.investigated_cases
        )

    @property
    def contradiction_rate(self) -> float:
        if self.investigated_cases == 0:
            return 0.0

        return (
            self.contradiction_cases
            / self.investigated_cases
        )

    @property
    def validation_rate(self) -> float:
        if self.investigated_cases == 0:
            return 0.0

        return (
            self.validated_cases
            / self.investigated_cases
        )

    @property
    def hypothesis_alignment_rate(self) -> float:
        if self.investigated_cases == 0:
            return 0.0

        return (
            self.hypothesis_aligned_cases
            / self.investigated_cases
        )

    @property
    def false_explanation_rate(self) -> float:
        if self.investigated_cases == 0:
            return 0.0

        return (
            self.false_explanation_cases
            / self.investigated_cases
        )

    @property
    def explanation_coverage(self) -> float:
        if self.total_discrepancy_amount == 0:
            return 1.0

        return float(
            self.total_explained_amount
            / self.total_discrepancy_amount
        )

    @property
    def throughput(self) -> float:
        if self.processing_time_ms <= Decimal("0"):
            return 0.0

        return (
            self.investigated_cases
            / float(
                self.processing_time_ms
                / Decimal("1000")
            )
        )


# ============================================================
# CORRUPTION -> EXPECTED HYPOTHESIS
# ============================================================


CORRUPTION_TO_HYPOTHESIS = {
    CorruptionType.MISSING_RECORD:
        HypothesisType.MISSING_EVENT,

    CorruptionType.DUPLICATE_RECORD:
        HypothesisType.DUPLICATE_EVENT,

    CorruptionType.AMOUNT_MISMATCH:
        HypothesisType.SOURCE_DATA_ERROR,

    CorruptionType.REFERENCE_MISMATCH:
        HypothesisType.SOURCE_DATA_ERROR,

    CorruptionType.TIMING_ANOMALY:
        HypothesisType.TIMING_DIFFERENCE,
}


def _expected_hypotheses_for_case(
    case_id: str,
    corruption_events,
) -> set[HypothesisType]:

    expected: set[HypothesisType] = set()

    for event in corruption_events:

        if event.case_id != case_id:
            continue

        hypothesis_type = (
            CORRUPTION_TO_HYPOTHESIS.get(
                event.corruption_type
            )
        )

        if hypothesis_type is not None:
            expected.add(hypothesis_type)

    return expected


# ============================================================
# HYPOTHESIS ALIGNMENT
# ============================================================


def _has_supported_expected_hypothesis(
    result: InvestigationResult,
    expected_hypotheses: set[HypothesisType],
) -> bool:

    for finding in result.hypotheses:

        if (
            finding.hypothesis_type
            not in expected_hypotheses
        ):
            continue

        if finding.status in {
            HypothesisStatus.SUPPORTED,
            HypothesisStatus.WEAKLY_SUPPORTED,
        }:
            return True

    return False


# ============================================================
# FALSE EXPLANATION
# ============================================================


def _is_false_explanation(
    result: InvestigationResult,
    expected_hypotheses: set[HypothesisType],
) -> bool:

    if result.explained_amount <= Decimal("0"):
        return False

    for finding in result.hypotheses:

        if finding.status not in {
            HypothesisStatus.SUPPORTED,
            HypothesisStatus.WEAKLY_SUPPORTED,
        }:
            continue

        if (
            finding.hypothesis_type
            in expected_hypotheses
        ):
            return False

    return True


# ============================================================
# BENCHMARK HELPERS
# ============================================================


def _corrupted_case_ids(benchmark) -> set[str]:

    return {
        event.case_id
        for event in benchmark.corruption_events
    }


def _is_fully_explained(
    result: InvestigationResult,
) -> bool:

    return (
        result.status
        == InvestigationStatus.RESOLVED
        and result.remaining_unexplained
        == Decimal("0")
        and result.explained_amount
        > Decimal("0")
    )


def _is_partially_explained(
    result: InvestigationResult,
) -> bool:

    return (
        result.explained_amount
        > Decimal("0")
        and result.remaining_unexplained
        > Decimal("0")
    )


# ============================================================
# PHASE 5 ADAPTER
# ============================================================


def _load_phase5_helpers():
    """
    Load the existing Phase 5 evaluation adapter.

    This works both when:

        pytest

    imports this module as:

        scripts.run_phase6_evaluation

    and when this file is executed directly:

        python scripts\\run_phase6_evaluation.py
    """

    try:

        from scripts.run_phase5_evaluation import (
            _build_case_records,
            _verify_case,
        )

    except ModuleNotFoundError:

        from run_phase5_evaluation import (
            _build_case_records,
            _verify_case,
        )

    try:

        from scripts.run_phase5_evaluation import (
            _apply_reference_state,
            _case_has_corruption,
        )

    except ModuleNotFoundError:

        from run_phase5_evaluation import (
            _apply_reference_state,
            _case_has_corruption,
        )

    return (
        _build_case_records,
        _verify_case,
        _apply_reference_state,
        _case_has_corruption,
    )


# ============================================================
# PHASE 6 EVALUATION
# ============================================================


def evaluate_phase6(
    num_cases: int = NUM_CASES,
    seed: int = SEED,
) -> Phase6Evaluation:

    started_at = perf_counter()

    benchmark = generate_benchmark(
        num_cases=num_cases,
        seed=seed,
    )

    corrupted_ids = _corrupted_case_ids(
        benchmark
    )

    total_cases = len(
        benchmark.ground_truth.cases
    )

    (
        build_case_records,
        verify_case,
        apply_reference_state,
        case_has_corruption,
    ) = _load_phase5_helpers()

    case_records = build_case_records(
        benchmark
    )

    # Phase 5 benchmark evaluation uses the clean benchmark state
    # as the reference for AMOUNT_MISMATCH cases. Phase 6 must
    # enter through the same evaluation boundary.
    clean_case_records = build_case_records(
        benchmark,
        benchmark.clean_records,
    )

    from app.evidence.relationship_resolver import (
        RelationshipResolver,
    )

    from app.reconciliation.resolver import (
        ReconciliationResolver,
    )

    from app.reconstruction.reconstructor import (
        Reconstructor,
    )

    from app.verification.verifier import (
        FinancialStateVerifier,
    )

    relationship_resolver = (
        RelationshipResolver()
    )

    reconciliation_resolver = (
        ReconciliationResolver()
    )

    reconstructor = Reconstructor()

    verifier = FinancialStateVerifier()

    case_builder = InvestigationCaseBuilder()

    investigation_service = (
        InvestigationService()
    )

    validator = InvestigationResultValidator()

    investigated_cases = 0

    fully_explained_cases = 0
    partially_explained_cases = 0

    unresolved_cases = 0
    insufficient_evidence_cases = 0
    contradiction_cases = 0

    validated_cases = 0
    investigated_discrepancies = 0

    hypothesis_aligned_cases = 0
    false_explanation_cases = 0

    total_explained_amount = Decimal("0")
    total_discrepancy_amount = Decimal("0")
    total_remaining_amount = Decimal("0")

    supporting_evidence_count = 0

    events_by_case: dict[str, list] = {}

    for event in benchmark.corruption_events:

        events_by_case.setdefault(
            event.case_id,
            [],
        ).append(event)

    runtime_failures: list[str] = []

    # --------------------------------------------------------
    # Process corrupted cases
    # --------------------------------------------------------

    for benchmark_case in (
        benchmark.ground_truth.cases
    ):

        case_id = benchmark_case.case_id

        if case_id not in corrupted_ids:
            continue

        records = case_records.get(
            case_id
        )

        if records is None:

            runtime_failures.append(
                f"{case_id}: case records not found"
            )

            continue

        # Case-level aggregation state. A corrupted benchmark case may
        # produce multiple Phase 5 discrepancies, but all quality metrics
        # below are counted once per benchmark case.
        case_investigated = False
        case_results: list[InvestigationResult] = []
        case_validation_attempted = False
        case_validation_passed = True
        case_hypothesis_aligned = False
        case_false_explanation = False

        try:

            # ------------------------------------------------
            # Exact Phase 5 pipeline
            # ------------------------------------------------

            reconstruction = verify_case(
                records,
                relationship_resolver=(
                    relationship_resolver
                ),
                reconciliation_resolver=(
                    reconciliation_resolver
                ),
                reconstructor=reconstructor,
            )

            if reconstruction is None:

                runtime_failures.append(
                    f"{case_id}: "
                    "Phase 5 reconstruction returned None"
                )

                continue

            # ------------------------------------------------
            # Clean/reference reconstruction
            # ------------------------------------------------

            clean_records = clean_case_records.get(
                case_id
            )

            if clean_records is None:

                runtime_failures.append(
                    f"{case_id}: clean case records not found"
                )

                continue

            clean_reconstruction = verify_case(
                clean_records,
                relationship_resolver=(
                    relationship_resolver
                ),
                reconciliation_resolver=(
                    reconciliation_resolver
                ),
                reconstructor=reconstructor,
            )

            if clean_reconstruction is None:

                runtime_failures.append(
                    f"{case_id}: "
                    "clean Phase 5 reconstruction returned None"
                )

                continue

            # ------------------------------------------------
            # Phase 5 verification
            # ------------------------------------------------

            verification = verifier.verify(
                reconstruction
            )

            # Production verification intentionally leaves the
            # expected bank credit unset. For the benchmark's
            # AMOUNT_MISMATCH corruption, reuse the existing
            # Phase 5 clean/reference adapter. Do not apply it
            # to unrelated corruption types.
            has_amount_mismatch = case_has_corruption(
                benchmark,
                case_id,
                CorruptionType.AMOUNT_MISMATCH,
            )

            if has_amount_mismatch:

                verification = apply_reference_state(
                    verification,
                    clean_reconstruction,
                    reconstruction,
                )

            if hasattr(
                verification,
                "model_copy",
            ):

                verification = (
                    verification.model_copy(
                        update={
                            "case_id": case_id,
                        }
                    )
                )

            else:

                verification.case_id = case_id

            # ------------------------------------------------
            # Phase 6 investigates every discrepancy actually
            # produced by Phase 5.
            # ------------------------------------------------

            if not verification.discrepancies:

                failure = (
                    f"{case_id}: "
                    "Phase 5 produced no discrepancies"
                )

                runtime_failures.append(
                    failure
                )

                continue

            expected_hypotheses = (
                _expected_hypotheses_for_case(
                    case_id,
                    events_by_case.get(
                        case_id,
                        [],
                    ),
                )
            )

            # ------------------------------------------------
            # Investigate discrepancies
            # ------------------------------------------------

            for discrepancy in (
                verification.discrepancies
            ):

                investigation_case = (
                    case_builder.build(
                        verification,
                        discrepancy,
                    )
                )

                service_result = (
                    investigation_service.investigate(
                        investigation_case,
                        reconstruction.event_graph,
                    )
                )

                result = service_result.result

                # ------------------------------------------------
                # TEMPORARY PHASE 6 DIAGNOSTIC
                # ------------------------------------------------
                # Only print cases where supporting evidence exists
                # but the final monetary explanation is zero.
                # This isolates the exact data-flow problem without
                # changing any Phase 6 behavior or benchmark metrics.
                if (
                    result.supporting_evidence_ids
                    and result.explained_amount == Decimal("0")
                ):
                    print()
                    print("=" * 70)
                    print("PHASE 6 ZERO-EXPLANATION DEBUG")
                    print("=" * 70)
                    print(f"CASE            : {investigation_case.case_id}")
                    print(f"DISCREPANCY     : {investigation_case.discrepancy_id}")
                    print(f"CONTROL         : {investigation_case.control_failure}")
                    print(f"EXPECTED        : {investigation_case.expected_value}")
                    print(f"OBSERVED        : {investigation_case.observed_value}")
                    print(f"DIFFERENCE      : {investigation_case.difference}")
                    print(
                        "AFFECTED EVENTS : "
                        f"{investigation_case.affected_event_ids}"
                    )
                    print(f"RESULT STATUS   : {result.status}")
                    print(f"EXPLAINED       : {result.explained_amount}")
                    print(
                        "REMAINING       : "
                        f"{result.remaining_unexplained}"
                    )
                    print(
                        "SUPPORTING IDS  : "
                        f"{result.supporting_evidence_ids}"
                    )
                    print("FINDINGS:")
                    for finding in result.hypotheses:
                        print(
                            f"  {finding.hypothesis_type.value} | "
                            f"STATUS={finding.status.value} | "
                            f"EXPLAINED={finding.explained_amount} | "
                            f"EVIDENCE={finding.evidence_ids}"
                        )
                    print("=" * 70)

                case_investigated = True
                case_results.append(result)
                investigated_discrepancies += 1

                # ------------------------------------------------
                # Monetary accounting
                #
                # Monetary totals remain discrepancy-level because
                # one benchmark case can legitimately contain more
                # than one financial discrepancy.
                # ------------------------------------------------

                if (
                    investigation_case.expected_value
                    is not None
                    and investigation_case.observed_value
                    is not None
                ):

                    discrepancy_amount = abs(
                        investigation_case.difference
                    )

                    total_discrepancy_amount += (
                        discrepancy_amount
                    )

                # ------------------------------------------------
                # Explanation accounting
                # ------------------------------------------------

                total_explained_amount += (
                    result.explained_amount
                )

                total_remaining_amount += (
                    result.remaining_unexplained
                )

                supporting_evidence_count += len(
                    result.supporting_evidence_ids
                )

                # ------------------------------------------------
                # Validation
                #
                # Validation is aggregated at CASE level. A case is
                # validated only when every investigation result for
                # that case passes the deterministic validator.
                # ------------------------------------------------

                case_validation_attempted = True

                try:

                    validated_result = (
                        validator.validate(
                            investigation_case,
                            result,
                        )
                    )

                    if not validated_result.validated:
                        case_validation_passed = False

                except Exception as exc:

                    case_validation_passed = False

                    failure = (
                        f"{case_id}/"
                        f"{discrepancy.discrepancy_id}: "
                        "validation failed: "
                        f"{type(exc).__name__}: {exc}"
                    )

                    runtime_failures.append(
                        failure
                    )

                # ------------------------------------------------
                # Case-level quality signals
                # ------------------------------------------------

                if _has_supported_expected_hypothesis(
                    result,
                    expected_hypotheses,
                ):

                    case_hypothesis_aligned = True

                if _is_false_explanation(
                    result,
                    expected_hypotheses,
                ):

                    case_false_explanation = True

            # ------------------------------------------------
            # Count each benchmark case once.
            # ------------------------------------------------

            if case_investigated:

                investigated_cases += 1

                # A case is validated only if every discrepancy-level
                # investigation in that case validated successfully.
                if (
                    case_validation_attempted
                    and case_validation_passed
                ):

                    validated_cases += 1

                if case_results:

                    all_fully_explained = all(
                        _is_fully_explained(result)
                        for result in case_results
                    )

                    any_explanation = any(
                        result.explained_amount
                        > Decimal("0")
                        for result in case_results
                    )

                    any_contradiction = any(
                        result.status
                        == InvestigationStatus.CONTRADICTION
                        for result in case_results
                    )

                    any_insufficient_evidence = any(
                        result.status
                        == InvestigationStatus.INSUFFICIENT_EVIDENCE
                        for result in case_results
                    )

                    any_unresolved = any(
                        result.status
                        == InvestigationStatus.UNRESOLVED
                        for result in case_results
                    )

                    if all_fully_explained:

                        fully_explained_cases += 1

                    elif any_explanation:

                        partially_explained_cases += 1

                    elif any_contradiction:

                        contradiction_cases += 1

                    elif any_insufficient_evidence:

                        insufficient_evidence_cases += 1

                    elif any_unresolved:

                        unresolved_cases += 1

                    if case_hypothesis_aligned:

                        hypothesis_aligned_cases += 1

                    if case_false_explanation:

                        false_explanation_cases += 1


        except Exception as exc:

            failure = (
                f"{case_id}: "
                f"{type(exc).__name__}: {exc}"
            )

            runtime_failures.append(
                failure
            )

            print()
            print("=" * 70)
            print("PHASE 6 CASE FAILURE")
            print("=" * 70)

            print(
                f"Case       : {case_id}"
            )

            print(
                f"Error type : {type(exc).__name__}"
            )

            print(
                f"Error      : {exc}"
            )

            print("=" * 70)

    # ========================================================
    # DIAGNOSTICS
    # ========================================================

    if runtime_failures:

        print()
        print("=" * 70)
        print("PHASE 6 DIAGNOSTICS")
        print("=" * 70)

        print(
            f"Runtime failures: "
            f"{len(runtime_failures)}"
        )

        for failure in runtime_failures:

            print(
                f" - {failure}"
            )

        print("=" * 70)

    # ========================================================
    # TIMING
    # ========================================================

    elapsed_ms = Decimal(
        str(
            (
                perf_counter()
                - started_at
            )
            * 1000
        )
    )

    # ========================================================
    # RESULT
    # ========================================================

    return Phase6Evaluation(

        total_cases=total_cases,

        corrupted_cases=len(
            corrupted_ids
        ),

        investigated_cases=(
            investigated_cases
        ),

        investigated_discrepancies=(
            investigated_discrepancies
        ),

        fully_explained_cases=(
            fully_explained_cases
        ),

        partially_explained_cases=(
            partially_explained_cases
        ),

        unresolved_cases=(
            unresolved_cases
        ),

        insufficient_evidence_cases=(
            insufficient_evidence_cases
        ),

        contradiction_cases=(
            contradiction_cases
        ),

        validated_cases=(
            validated_cases
        ),

        hypothesis_aligned_cases=(
            hypothesis_aligned_cases
        ),

        false_explanation_cases=(
            false_explanation_cases
        ),

        total_explained_amount=(
            total_explained_amount
        ),

        total_discrepancy_amount=(
            total_discrepancy_amount
        ),

        total_remaining_amount=(
            total_remaining_amount
        ),

        supporting_evidence_count=(
            supporting_evidence_count
        ),

        processing_time_ms=(
            elapsed_ms
        ),
    )


# ============================================================
# REPORT
# ============================================================


def print_phase6_report(
    evaluation: Phase6Evaluation,
) -> None:

    print()
    print("=" * 70)
    print(
        "PHASE 6 INVESTIGATION EVALUATION"
    )
    print("=" * 70)

    print()
    print("CONFIGURATION")
    print("-" * 70)

    print(
        f"Benchmark cases : "
        f"{evaluation.total_cases}"
    )

    print(
        f"Corrupted cases : "
        f"{evaluation.corrupted_cases}"
    )

    print()
    print("=" * 70)
    print("PHASE 6 RESULTS")
    print("=" * 70)

    print()

    print(
        f"Total benchmark cases       : "
        f"{evaluation.total_cases}"
    )

    print(
        f"Corrupted cases             : "
        f"{evaluation.corrupted_cases}"
    )

    print(
        f"Investigated cases          : "
        f"{evaluation.investigated_cases}"
    )

    print(
        f"Investigated discrepancies   : "
        f"{evaluation.investigated_discrepancies}"
    )

    print(
        f"Investigation coverage      : "
        f"{evaluation.investigation_coverage:.2%}"
    )

    print()

    print(
        f"Fully explained             : "
        f"{evaluation.fully_explained_cases}"
    )

    print(
        f"Full explanation rate       : "
        f"{evaluation.full_explanation_rate:.2%}"
    )

    print(
        f"Partially explained         : "
        f"{evaluation.partially_explained_cases}"
    )

    print(
        f"Partial explanation rate    : "
        f"{evaluation.partial_explanation_rate:.2%}"
    )

    print(
        f"Unresolved                  : "
        f"{evaluation.unresolved_cases}"
    )

    print(
        f"Unresolved rate             : "
        f"{evaluation.unresolved_rate:.2%}"
    )

    print(
        f"Insufficient evidence       : "
        f"{evaluation.insufficient_evidence_cases}"
    )

    print(
        f"Contradictions              : "
        f"{evaluation.contradiction_cases}"
    )

    print(
        f"Validation rate             : "
        f"{evaluation.validation_rate:.2%}"
    )

    print()

    print(
        f"Hypothesis aligned          : "
        f"{evaluation.hypothesis_aligned_cases}"
    )

    print(
        f"Hypothesis alignment rate  : "
        f"{evaluation.hypothesis_alignment_rate:.2%}"
    )

    print(
        f"False explanations          : "
        f"{evaluation.false_explanation_cases}"
    )

    print(
        f"False explanation rate      : "
        f"{evaluation.false_explanation_rate:.2%}"
    )

    print()

    print(
        f"Total monetary discrepancy : "
        f"{evaluation.total_discrepancy_amount}"
    )

    print(
        f"Total explained amount     : "
        f"{evaluation.total_explained_amount}"
    )

    print(
        f"Total remaining amount     : "
        f"{evaluation.total_remaining_amount}"
    )

    print(
        f"Explanation coverage       : "
        f"{evaluation.explanation_coverage:.2%}"
    )

    print()

    print(
        f"Supporting evidence items : "
        f"{evaluation.supporting_evidence_count}"
    )

    print(
        f"Processing time            : "
        f"{evaluation.processing_time_ms:.4f} ms"
    )

    print(
        f"Investigation throughput   : "
        f"{evaluation.throughput:.2f} cases/sec"
    )

    print()

    print("=" * 70)
    print(
        "PHASE 6 EVALUATION COMPLETE"
    )
    print("=" * 70)


# ============================================================
# PUBLIC RUNNER
# ============================================================


def run_phase6_evaluation() -> Phase6Evaluation:

    evaluation = evaluate_phase6(
        num_cases=NUM_CASES,
        seed=SEED,
    )

    print_phase6_report(
        evaluation
    )

    return evaluation


# ============================================================
# SCRIPT ENTRY POINT
# ============================================================


if __name__ == "__main__":

    run_phase6_evaluation()