from collections import defaultdict
from app.domain.enums import EventType

from app.benchmark import generate_benchmark
from app.corruption.models import CorruptionType

from app.reconciliation.aggregator import (
    aggregate_records,
)
from app.reconciliation.matcher import (
    reconcile_case,
)
from app.reconstruction.reconstructor import (
    Reconstructor,
)
from app.reconciliation.graph import (
    ReconciliationGraph,
)

from app.verification.evaluator import (
    GroundTruthVerification,
    VerificationEvaluator,
)
from app.verification.evaluation import (
    VerificationEvaluation,
)
from app.verification.verifier import (
    FinancialStateVerifier,
)
from app.verification.discrepancy import (
    DiscrepancyBuilder,
)
from app.verification.invariants import (
    run_invariants,
)
from app.verification.models import (
    ControlStatus,
    VerificationStatus,
)


# ============================================================
# Corruption -> Phase 5 control mapping
# ============================================================

CORRUPTION_TO_CONTROLS = {
    CorruptionType.MISSING_RECORD: frozenset(
        {
            "SETTLEMENT_BANK_COMPLETENESS",
        }
    ),
    CorruptionType.DUPLICATE_RECORD: frozenset(
        {
            "DUPLICATE_EVENT",
        }
    ),
    CorruptionType.AMOUNT_MISMATCH: frozenset(
        {
            "BANK_CREDIT_AMOUNT",
        }
    ),
    CorruptionType.REFERENCE_MISMATCH: frozenset(
        {
            "PAYMENT_SETTLEMENT_COMPLETENESS",
        }
    ),
    CorruptionType.TIMING_ANOMALY: frozenset(
        {
            "EVENT_ORDERING",
            "SETTLEMENT_TIMING",
            "CHAIN_TEMPORAL_ORDER",
        }
    ),
}


MATERIAL_CORRUPTIONS = {
    CorruptionType.MISSING_RECORD,
    CorruptionType.AMOUNT_MISMATCH,
    CorruptionType.REFERENCE_MISMATCH,
    CorruptionType.TIMING_ANOMALY,
}


# ============================================================
# Reconstruction
# ============================================================

def _reconstruct_benchmark_case(
    case_id: str,
    records: dict[str, list],
    reconstructor: Reconstructor,
):
    """
    Reconcile and reconstruct one benchmark case.

    This function belongs exclusively to the evaluation layer.

    It does not expose benchmark ground truth to the runtime
    verifier.
    """

    cases = aggregate_records(records)

    case = cases.get(case_id)

    if case is None or case.payment is None:
        return None

    result = reconcile_case(
        case_id=case.case_id,
        payment_amount=case.payment.amount,
        refund_amount=case.refund_amount,
        fee_amount=case.fee_amount,
        settlement_amount=case.settlement_amount,
        bank_amount=case.bank_amount,
    )

    reconciliation_graph = result.graph

    return reconstructor.reconstruct(
        reconciliation_graph
    )


# ============================================================
# Independent benchmark financial state
# ============================================================

def _reference_financial_state(
    reconstruction,
):
    """
    Extract the independently reconstructed clean financial
    state used as the benchmark reference.

    This helper is evaluation-only.

    The clean reconstruction is generated from
    benchmark.clean_records, never from the corrupted
    observed records.

    The reconstruction result exposes its financial information
    through batch_state. There is no reconstruction.state object.
    """

    batch_state = reconstruction.batch_state

    return {
        "gross_captured": (
            batch_state.total_gross_amount
        ),
        "total_refunded": (
            batch_state.total_refund_amount
        ),
        "total_fees": (
            batch_state.total_fee_amount
        ),
        "total_adjustments": (
            batch_state.total_adjustment_amount
        ),
        "expected_settlement": (
            batch_state.total_observed_net_amount
        ),
        "expected_bank_credit": (
            batch_state.total_bank_credit_amount
        ),
    }


# ============================================================
# Benchmark verification adapter
# ============================================================

def _apply_reference_state(
    verification,
    clean_reconstruction,
    observed_reconstruction,
):
    """
    Attach the independent clean/reference financial state to
    a VerificationResult and recompute only the controls whose
    expected values depend on that financial state.

    Production verification is not changed.

    Evaluation semantics:

        expected = clean/reference reconstruction
        observed = corrupted reconstruction

    Structural, temporal, completeness, duplicate, and currency
    controls continue to operate on the observed reconstruction.

    Provenance is preserved for benchmark-recomputed invariant
    controls so that Phase 6 can trace a discrepancy back to the
    actual observed events that produced it.
    """

    reference = _reference_financial_state(
        clean_reconstruction
    )

    # --------------------------------------------------------
    # Build the expected financial state from the existing
    # verification result, but replace its financial values with
    # the independent clean/reference values.
    # --------------------------------------------------------

    expected_state = verification.expected_state

    if hasattr(
        expected_state,
        "model_copy",
    ):
        expected_state = expected_state.model_copy(
            update={
                "gross_captured": (
                    reference["gross_captured"]
                ),
                "total_refunded": (
                    reference["total_refunded"]
                ),
                "total_fees": (
                    reference["total_fees"]
                ),
                "total_adjustments": (
                    reference["total_adjustments"]
                ),
                "expected_settlement": (
                    reference["expected_settlement"]
                ),
                "expected_bank_credit": (
                    reference["expected_bank_credit"]
                ),
            }
        )
    else:
        # Defensive fallback for dataclass-style models.
        expected_state.gross_captured = (
            reference["gross_captured"]
        )
        expected_state.total_refunded = (
            reference["total_refunded"]
        )
        expected_state.total_fees = (
            reference["total_fees"]
        )
        expected_state.total_adjustments = (
            reference["total_adjustments"]
        )
        expected_state.expected_settlement = (
            reference["expected_settlement"]
        )
        expected_state.expected_bank_credit = (
            reference["expected_bank_credit"]
        )

    # --------------------------------------------------------
    # Re-run ONLY financial invariant controls using:
    #
    #     expected = clean reference
    #     observed = corrupted reconstruction
    #
    # This is benchmark-only evaluation logic.
    # --------------------------------------------------------

    observed_batch_state = (
        observed_reconstruction.batch_state
    )

    reference_invariant_controls = run_invariants(
        expected_state,
        observed_batch_state,
    )

    # --------------------------------------------------------
    # Preserve provenance for the newly-created invariant
    # controls.
    #
    # run_invariants() intentionally operates only on financial
    # state and therefore does not know which graph events
    # produced each aggregate amount.
    #
    # The benchmark adapter does know the observed reconstruction
    # graph, so it attaches event provenance here.
    #
    # This does NOT change:
    #   - status
    #   - expected value
    #   - observed value
    #   - difference
    #
    # It only makes the failed control traceable.
    # --------------------------------------------------------

    control_event_types = {
        "SETTLEMENT_AMOUNT": {
            EventType.SETTLEMENT_CREATED,
            EventType.SETTLEMENT_PROCESSED,
        },
        "BANK_CREDIT_AMOUNT": {
            EventType.BANK_CREDIT,
        },
        "REFUND_AMOUNT": {
            EventType.REFUND_CREATED,
        },
        "FEE_AMOUNT": {
            EventType.FEE_APPLIED,
        },
        "ADJUSTMENT_AMOUNT": {
            EventType.ADJUSTMENT_APPLIED,
        },
    }

    enriched_controls = []

    for control in reference_invariant_controls:
        event_types = control_event_types.get(
            control.control_id
        )

        # Only enrich failed controls and only when provenance
        # has not already been attached.
        if (
            control.status == ControlStatus.FAIL
            and event_types
            and not control.affected_event_ids
        ):
            affected_event_ids = [
                event.event_id
                for event in (
                    observed_reconstruction
                    .event_graph
                    .events
                    .values()
                )
                if event.event_type in event_types
            ]

            if affected_event_ids:
                control = control.model_copy(
                    update={
                        "affected_event_ids": (
                            affected_event_ids
                        ),
                    }
                )

        enriched_controls.append(control)

    reference_invariant_controls = (
        enriched_controls
    )

    invariant_control_ids = {
        control.control_id
        for control in reference_invariant_controls
    }

    # --------------------------------------------------------
    # Preserve all non-invariant controls generated from the
    # actual observed event graph.
    # --------------------------------------------------------

    non_invariant_controls = [
        control
        for control in verification.controls
        if control.control_id
        not in invariant_control_ids
    ]

    controls = (
        reference_invariant_controls
        + non_invariant_controls
    )

    # --------------------------------------------------------
    # Rebuild discrepancies from the corrected control set.
    #
    # The original discrepancies were generated from the old
    # invariant results, so they must also be regenerated.
    # --------------------------------------------------------

    discrepancy_builder = DiscrepancyBuilder()

    discrepancies = []

    for control in controls:
        discrepancy = discrepancy_builder.build(
            control
        )

        if discrepancy is not None:
            discrepancies.append(
                discrepancy
            )

    # --------------------------------------------------------
    # Recalculate overall verification status using the
    # corrected controls.
    # --------------------------------------------------------

    if any(
        control.status == ControlStatus.FAIL
        for control in controls
    ):
        status = VerificationStatus.FAILED

    else:
        applicable_controls = [
            control
            for control in controls
            if control.status
            not in {
                ControlStatus.PENDING,
                ControlStatus.NOT_APPLICABLE,
            }
        ]

        if any(
            control.status == ControlStatus.PASS
            for control in applicable_controls
        ):
            status = VerificationStatus.VERIFIED

        else:
            status = VerificationStatus.PENDING

    # --------------------------------------------------------
    # Update expected state, controls, discrepancies and status.
    # --------------------------------------------------------

    if hasattr(
        verification,
        "model_copy",
    ):
        return verification.model_copy(
            update={
                "expected_state": expected_state,
                "controls": controls,
                "discrepancies": discrepancies,
                "status": status,
            }
        )

    verification.expected_state = (
        expected_state
    )
    verification.controls = controls
    verification.discrepancies = discrepancies
    verification.status = status

    return verification

# ============================================================
# Ground-truth construction
# ============================================================

def build_ground_truth(
    corruption_events,
    case_ids: list[str],
) -> list[GroundTruthVerification]:
    """
    Convert benchmark corruption events into evaluation-only
    verification ground truth.

    The runtime verifier never receives this information.
    """

    failed_controls = defaultdict(set)
    material_controls = defaultdict(set)
    discrepancy_controls = defaultdict(set)

    for event in corruption_events:

        controls = CORRUPTION_TO_CONTROLS.get(
            event.corruption_type,
            frozenset(),
        )

        for control_id in controls:

            failed_controls[
                event.case_id
            ].add(control_id)

            discrepancy_controls[
                event.case_id
            ].add(control_id)

            if (
                event.corruption_type
                in MATERIAL_CORRUPTIONS
            ):
                material_controls[
                    event.case_id
                ].add(control_id)

    return [
        GroundTruthVerification(
            failed_controls=frozenset(
                failed_controls.get(
                    case_id,
                    set(),
                )
            ),
            material_failed_controls=frozenset(
                material_controls.get(
                    case_id,
                    set(),
                )
            ),
            discrepancy_controls=frozenset(
                discrepancy_controls.get(
                    case_id,
                    set(),
                )
            ),
        )
        for case_id in case_ids
    ]


# ============================================================
# Full Phase 5 benchmark
# ============================================================

def evaluate_phase5(
    num_cases: int = 100,
    seed: int = 42,
) -> VerificationEvaluation:
    """
    Run the complete Phase 5 verification evaluation.

    Benchmark architecture:

        clean_records
             |
             v
        clean reconstruction
             |
             v
        independent expected state

        observed_records
             |
             v
        observed reconstruction
             |
             v
        runtime verification
             |
             v
        expected/reference adapter
             |
             v
        VerificationResult
             |
             v
        GroundTruthVerification
             |
             v
        VerificationEvaluator

    The clean benchmark state is used only by this evaluation
    layer. It is never supplied to the production verifier.
    """

    benchmark = generate_benchmark(
        num_cases=num_cases,
        seed=seed,
    )

    case_ids = [
        case.case_id
        for case in benchmark.ground_truth.cases
    ]

    reconstructor = Reconstructor()

    verifier = FinancialStateVerifier()

    results = []

    # --------------------------------------------------------
    # Preserve explicit case/result association.
    #
    # Never infer a case ID from result position.
    # --------------------------------------------------------

    result_case_ids = []

    for case_id in case_ids:

        observed_reconstruction = (
            _reconstruct_benchmark_case(
                case_id,
                benchmark.observed_records,
                reconstructor,
            )
        )

        if observed_reconstruction is None:
            continue

        clean_reconstruction = (
            _reconstruct_benchmark_case(
                case_id,
                benchmark.clean_records,
                reconstructor,
            )
        )

        if clean_reconstruction is None:
            continue

        verification = verifier.verify(
            observed_reconstruction
        )

        # ----------------------------------------------------
        # Attach the independent clean/reference financial
        # state to the benchmark result and recompute only
        # financial invariant controls.
        # ----------------------------------------------------

        verification = _apply_reference_state(
            verification,
            clean_reconstruction,
            observed_reconstruction,
        )

        # ----------------------------------------------------
        # Preserve the actual benchmark case ID.
        # ----------------------------------------------------

        if hasattr(
            verification,
            "model_copy",
        ):
            verification = verification.model_copy(
                update={
                    "case_id": case_id,
                }
            )
        else:
            verification.case_id = case_id

        results.append(
            verification
        )

        result_case_ids.append(
            case_id
        )

    # --------------------------------------------------------
    # Ground truth
    # --------------------------------------------------------

    ground_truth_by_case = {
        case_id: ground_truth
        for case_id, ground_truth in zip(
            case_ids,
            build_ground_truth(
                benchmark.corruption_events,
                case_ids,
            ),
        )
    }

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Match ground truth using the actual result case ID,
    # never using positional slicing.
    # --------------------------------------------------------

    evaluated_ground_truth = [
        ground_truth_by_case[
            case_id
        ]
        for case_id in result_case_ids
        if case_id in ground_truth_by_case
    ]

    # --------------------------------------------------------
    # Only evaluate matching result/ground-truth pairs.
    # --------------------------------------------------------

    paired_results = []

    paired_ground_truth = []

    for result, case_id in zip(
        results,
        result_case_ids,
    ):

        ground_truth = (
            ground_truth_by_case.get(
                case_id
            )
        )

        if ground_truth is None:
            continue

        paired_results.append(
            result
        )

        paired_ground_truth.append(
            ground_truth
        )

    return VerificationEvaluator().evaluate(
        paired_results,
        paired_ground_truth,
    )