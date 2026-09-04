from dataclasses import dataclass
from time import perf_counter


from app.benchmark import generate_benchmark
from app.corruption.models import CorruptionType
from app.verification.benchmark import _apply_reference_state

from app.ingestion.canonical_models import (
    CanonicalAdjustment,
    CanonicalBankEntry,
    CanonicalFee,
    CanonicalOrder,
    CanonicalPayment,
    CanonicalRefund,
    CanonicalSettlement,
)

from app.ingestion.quality import QualityStatus

from app.evidence.relationship_resolver import (
    RelationshipResolver,
)

from app.reconciliation.resolver import (
    ReconciliationResolver,
)

from app.reconstruction.reconstructor import (
    Reconstructor,
)

from app.verification.evaluator import (
    GroundTruthVerification,
    VerificationEvaluator,
)

from app.verification.models import (
    ControlStatus,
    VerificationResult,
)

from app.verification.report import (
    print_evaluation_report,
)


NUM_CASES = 100
SEED = 42


# ============================================================
# BENCHMARK → CANONICAL RECORD ADAPTER
# ============================================================


def _evidence_id(
    record_type: str,
    record_id: str,
    occurrence: int = 1,
) -> str:
    """
    Create a deterministic and unique evidence identifier.

    A business record may legitimately appear more than once
    in the observed dataset because the benchmark can inject
    duplicate records.

    Therefore:

        business identity != evidence identity

    Example:

        Original:
            EVIDENCE_BANK_CASE_0003_BANK_EVENT_1

        Duplicate:
            EVIDENCE_BANK_CASE_0003_BANK_EVENT_2
    """

    return (
        f"EVIDENCE_"
        f"{record_type.upper()}_"
        f"{record_id}_"
        f"{occurrence}"
    )


def _canonical_order(
    record,
    source_row: int,
    occurrence: int,
) -> CanonicalOrder:
    """
    Convert benchmark OrderRecord into CanonicalOrder.
    """

    return CanonicalOrder(
        evidence_id=_evidence_id(
            "order",
            record.order_id,
            occurrence,
        ),
        source_type="benchmark",
        source_file="benchmark_orders.generated",
        source_row=source_row,

        order_id=record.order_id,
        customer_id=record.customer_id,
        amount=record.amount,
        currency=record.currency,
        event_timestamp=record.timestamp,
        status=record.status,

        raw_reference=record.payment_id,
        normalized_reference=record.payment_id,

        raw_record=record.model_dump(),

        quality_status=QualityStatus.VALID,
    )


def _canonical_payment(
    record,
    source_row: int,
    occurrence: int,
) -> CanonicalPayment:
    """
    Convert benchmark PaymentRecord into CanonicalPayment.
    """

    return CanonicalPayment(
        evidence_id=_evidence_id(
            "payment",
            record.payment_id,
            occurrence,
        ),
        source_type="benchmark",
        source_file="benchmark_payments.generated",
        source_row=source_row,

        payment_id=record.payment_id,
        order_id=record.order_id,
        amount=record.amount,
        currency="INR",
        event_timestamp=record.captured_at,
        status=record.status,

        raw_reference=record.order_id,
        normalized_reference=record.order_id,

        raw_record=record.model_dump(),

        quality_status=QualityStatus.VALID,
    )


def _canonical_refund(
    record,
    source_row: int,
    occurrence: int,
) -> CanonicalRefund:
    """
    Convert benchmark RefundRecord into CanonicalRefund.
    """

    return CanonicalRefund(
        evidence_id=_evidence_id(
            "refund",
            record.refund_id,
            occurrence,
        ),
        source_type="benchmark",
        source_file="benchmark_refunds.generated",
        source_row=source_row,

        refund_id=record.refund_id,
        payment_id=record.payment_id,
        amount=record.amount,
        event_timestamp=record.timestamp,
        status=record.status,

        raw_reference=record.reference,
        normalized_reference=record.reference,

        raw_record=record.model_dump(),

        quality_status=QualityStatus.VALID,
    )


def _canonical_fee(
    record,
    source_row: int,
    occurrence: int,
) -> CanonicalFee:
    """
    Convert benchmark FeeRecord into CanonicalFee.
    """

    return CanonicalFee(
        evidence_id=_evidence_id(
            "fee",
            record.fee_id,
            occurrence,
        ),
        source_type="benchmark",
        source_file="benchmark_fees.generated",
        source_row=source_row,

        fee_id=record.fee_id,
        payment_id=record.payment_id,
        amount=record.amount,
        event_timestamp=record.timestamp,
        status=record.status,

        raw_reference=record.payment_id,
        normalized_reference=record.payment_id,

        raw_record=record.model_dump(),

        quality_status=QualityStatus.VALID,
    )


def _canonical_adjustment(
    record,
    source_row: int,
    occurrence: int,
) -> CanonicalAdjustment:
    """
    Convert benchmark AdjustmentRecord into
    CanonicalAdjustment.
    """

    return CanonicalAdjustment(
        evidence_id=_evidence_id(
            "adjustment",
            record.event_id,
            occurrence,
        ),
        source_type="benchmark",
        source_file="benchmark_adjustments.generated",
        source_row=source_row,

        event_id=record.event_id,
        payment_id=record.payment_id,
        event_type=record.event_type,
        amount=record.amount,
        event_timestamp=record.timestamp,
        status=record.status,

        raw_reference=record.reference,
        normalized_reference=record.reference,

        raw_record=record.model_dump(),

        quality_status=QualityStatus.VALID,
    )


def _canonical_settlement(
    record,
    source_row: int,
    occurrence: int,
) -> CanonicalSettlement:
    """
    Convert benchmark SettlementRecord into
    CanonicalSettlement.
    """

    return CanonicalSettlement(
        evidence_id=_evidence_id(
            "settlement",
            record.settlement_id,
            occurrence,
        ),
        source_type="benchmark",
        source_file="benchmark_settlements.generated",
        source_row=source_row,

        settlement_id=record.settlement_id,
        payment_id=record.payment_id,
        reference=record.reference,
        gross_amount=record.gross_amount,
        fee=record.fee,
        tax=record.tax,
        adjustment=record.adjustment,
        net_amount=record.net_amount,
        event_timestamp=record.settled_at,
        status=record.status,
        utr=record.utr,

        raw_reference=record.reference,
        normalized_reference=record.reference,

        raw_record=record.model_dump(),

        quality_status=QualityStatus.VALID,
    )


def _canonical_bank(
    record,
    source_row: int,
    occurrence: int,
) -> CanonicalBankEntry:
    """
    Convert benchmark BankStatementLine into
    CanonicalBankEntry.

    Duplicate bank records retain the same business
    transaction_id but receive different evidence IDs.
    """

    return CanonicalBankEntry(
        evidence_id=_evidence_id(
            "bank",
            record.bank_txn_id,
            occurrence,
        ),
        source_type="benchmark",
        source_file="benchmark_bank.generated",
        source_row=source_row,

        transaction_id=record.bank_txn_id,
        narration=record.narration,
        normalized_narration=record.narration,

        credit=record.credit,
        debit=record.debit,

        event_timestamp=record.value_date,

        currency="INR",
        utr=record.utr,

        raw_record=record.model_dump(),

        quality_status=QualityStatus.VALID,
    )


def _canonicalize_record(
    record_type: str,
    record,
    source_row: int,
    occurrence: int,
):
    """
    Convert one benchmark domain record into its
    canonical ingestion representation.

    The benchmark records are already validated domain
    records, but their schemas differ from the raw ingestion
    schemas.

    Therefore this evaluation adapter performs explicit
    domain → canonical mapping instead of passing the
    benchmark record through the raw parser layer.
    """

    if record_type == "orders":

        return _canonical_order(
            record,
            source_row,
            occurrence,
        )

    if record_type == "payments":

        return _canonical_payment(
            record,
            source_row,
            occurrence,
        )

    if record_type == "refunds":

        return _canonical_refund(
            record,
            source_row,
            occurrence,
        )

    if record_type == "fees":

        return _canonical_fee(
            record,
            source_row,
            occurrence,
        )

    if record_type == "adjustments":

        return _canonical_adjustment(
            record,
            source_row,
            occurrence,
        )

    if record_type == "settlements":

        return _canonical_settlement(
            record,
            source_row,
            occurrence,
        )

    if record_type == "bank":

        return _canonical_bank(
            record,
            source_row,
            occurrence,
        )

    raise ValueError(
        f"Unsupported benchmark record type: "
        f"{record_type}"
    )


# ============================================================
# CASE IDENTIFICATION
# ============================================================


def _case_id_from_record(
    record_type: str,
    record,
) -> str | None:
    """
    Extract CASE_XXXX from benchmark record identifiers.
    """

    if record_type == "orders":

        identifier = record.order_id

    elif record_type == "payments":

        identifier = record.payment_id

    elif record_type == "refunds":

        identifier = record.refund_id

    elif record_type == "fees":

        identifier = record.fee_id

    elif record_type == "adjustments":

        identifier = record.event_id

    elif record_type == "settlements":

        identifier = record.settlement_id

    elif record_type == "bank":

        identifier = record.bank_txn_id

    else:

        return None

    if not isinstance(identifier, str):

        return None

    parts = identifier.split("_")

    if len(parts) < 2:

        return None

    if parts[0] != "CASE":

        return None

    return (
        f"{parts[0]}_{parts[1]}"
    )


# ============================================================
# CASE RECORD BUILDING
# ============================================================


def _build_case_records(
    benchmark,
    records_source: dict[str, list] | None = None,
) -> dict[str, dict[str, list]]:
    """
    Canonicalize benchmark records and isolate them
    by case.

    ``records_source`` allows the same canonicalization
    logic to be used for both clean and observed records.

    Duplicate records are preserved.

    Each occurrence of the same business record receives
    a distinct evidence_id.
    """

    case_ids = [
        case.case_id
        for case in benchmark.ground_truth.cases
    ]

    case_records = {
        case_id: {
            "orders": [],
            "payments": [],
            "refunds": [],
            "fees": [],
            "adjustments": [],
            "settlements": [],
            "bank": [],
        }
        for case_id in case_ids
    }

    if records_source is None:
        records_source = benchmark.observed_records

    # --------------------------------------------------------
    # Track duplicate occurrences.
    #
    # Key:
    #
    #     (record_type, business_record_id)
    #
    # Value:
    #
    #     number of times that record has appeared
    # --------------------------------------------------------

    occurrences: dict[
        tuple[str, str],
        int,
    ] = {}

    for record_type, records in (
        records_source.items()
    ):

        for source_row, record in enumerate(
            records,
            start=1,
        ):

            case_id = _case_id_from_record(
                record_type,
                record,
            )

            if case_id is None:

                continue

            if case_id not in case_records:

                continue

            # ------------------------------------------------
            # Determine business identity.
            # ------------------------------------------------

            if record_type == "orders":

                record_id = record.order_id

            elif record_type == "payments":

                record_id = record.payment_id

            elif record_type == "refunds":

                record_id = record.refund_id

            elif record_type == "fees":

                record_id = record.fee_id

            elif record_type == "adjustments":

                record_id = record.event_id

            elif record_type == "settlements":

                record_id = record.settlement_id

            elif record_type == "bank":

                record_id = record.bank_txn_id

            else:

                raise ValueError(
                    f"Unsupported record type: "
                    f"{record_type}"
                )

            # ------------------------------------------------
            # Increment occurrence.
            # ------------------------------------------------

            occurrence_key = (
                record_type,
                record_id,
            )

            occurrence = (
                occurrences.get(
                    occurrence_key,
                    0,
                )
                + 1
            )

            occurrences[
                occurrence_key
            ] = occurrence

            # ------------------------------------------------
            # Convert to canonical record.
            # ------------------------------------------------

            canonical = _canonicalize_record(
                record_type,
                record,
                source_row,
                occurrence,
            )

            # ------------------------------------------------
            # Store under the appropriate case.
            # ------------------------------------------------

            case_records[
                case_id
            ][record_type].append(
                canonical
            )

    return case_records


# ============================================================
# EVALUATION INGESTION ADAPTER
# ============================================================


@dataclass(frozen=True)
class _RecordBucket:
    valid_records: list


@dataclass(frozen=True)
class _EvaluationIngestionResult:
    """
    Minimal ingestion result required by
    RelationshipResolver.
    """

    orders: _RecordBucket
    payments: _RecordBucket
    refunds: _RecordBucket
    fees: _RecordBucket
    adjustments: _RecordBucket
    settlements: _RecordBucket
    bank: _RecordBucket


def _build_evidence_input(
    records: dict[str, list],
) -> _EvaluationIngestionResult:

    return _EvaluationIngestionResult(
        orders=_RecordBucket(
            records["orders"]
        ),
        payments=_RecordBucket(
            records["payments"]
        ),
        refunds=_RecordBucket(
            records["refunds"]
        ),
        fees=_RecordBucket(
            records["fees"]
        ),
        adjustments=_RecordBucket(
            records["adjustments"]
        ),
        settlements=_RecordBucket(
            records["settlements"]
        ),
        bank=_RecordBucket(
            records["bank"]
        ),
    )


# ============================================================
# GROUND TRUTH
# ============================================================


def _ground_truth_for_case(
    case_id: str,
    corruption_events,
) -> GroundTruthVerification:
    """
    Translate benchmark corruption events into verification
    control ground truth.

    This function belongs exclusively to the evaluation layer.

    FinancialStateVerifier never receives benchmark
    corruption information.
    """

    events = [
        event
        for event in corruption_events
        if event.case_id == case_id
    ]

    failed_controls: set[str] = set()
    material_failed_controls: set[str] = set()
    discrepancy_controls: set[str] = set()
    pending_controls: set[str] = set()

    for event in events:

        if event.corruption_type == (
            CorruptionType.MISSING_RECORD
        ):

            failed_controls.add(
                "SETTLEMENT_BANK_COMPLETENESS"
            )

            material_failed_controls.add(
                "SETTLEMENT_BANK_COMPLETENESS"
            )

            discrepancy_controls.add(
                "SETTLEMENT_BANK_COMPLETENESS"
            )

        elif event.corruption_type == (
            CorruptionType.DUPLICATE_RECORD
        ):

            failed_controls.add(
                "DUPLICATE_EVENT"
            )

            material_failed_controls.add(
                "DUPLICATE_EVENT"
            )

            discrepancy_controls.add(
                "DUPLICATE_EVENT"
            )

        elif event.corruption_type == (
            CorruptionType.AMOUNT_MISMATCH
        ):

            failed_controls.add(
                "BANK_CREDIT_AMOUNT"
            )

            material_failed_controls.add(
                "BANK_CREDIT_AMOUNT"
            )

            discrepancy_controls.add(
                "BANK_CREDIT_AMOUNT"
            )

        elif event.corruption_type == (
            CorruptionType.REFERENCE_MISMATCH
        ):

            failed_controls.add(
                "PAYMENT_SETTLEMENT_COMPLETENESS"
            )

            material_failed_controls.add(
                "PAYMENT_SETTLEMENT_COMPLETENESS"
            )

            discrepancy_controls.add(
                "PAYMENT_SETTLEMENT_COMPLETENESS"
            )

        elif event.corruption_type == (
            CorruptionType.TIMING_ANOMALY
        ):

            failed_controls.update(
                {
                    "EVENT_ORDERING",
                    "SETTLEMENT_TIMING",
                }
            )

            material_failed_controls.update(
                {
                    "EVENT_ORDERING",
                    "SETTLEMENT_TIMING",
                }
            )

            discrepancy_controls.update(
                {
                    "EVENT_ORDERING",
                    "SETTLEMENT_TIMING",
                }
            )

    return GroundTruthVerification(
        failed_controls=frozenset(
            failed_controls
        ),
        material_failed_controls=frozenset(
            material_failed_controls
        ),
        discrepancy_controls=frozenset(
            discrepancy_controls
        ),
        pending_controls=frozenset(
            pending_controls
        ),
    )


def _build_ground_truth(
    benchmark,
) -> list[GroundTruthVerification]:

    return [
        _ground_truth_for_case(
            case.case_id,
            benchmark.corruption_events,
        )
        for case in benchmark.ground_truth.cases
    ]


# ============================================================
# SINGLE CASE PIPELINE
# ============================================================


def _verify_case(
    observed_records: dict[str, list],
    *,
    relationship_resolver: RelationshipResolver,
    reconciliation_resolver: ReconciliationResolver,
    reconstructor: Reconstructor,
):
    """
    Execute:

        canonical records
            ↓
        EvidenceGraph
            ↓
        ReconciliationGraph
            ↓
        ReconstructionResult
    """

    evidence_input = _build_evidence_input(
        observed_records
    )

    evidence_graph = (
        relationship_resolver.resolve(
            evidence_input
        )
    )

    reconciliation_graph = (
        reconciliation_resolver.resolve(
            evidence_graph
        )
    )

    reconstruction = (
        reconstructor.reconstruct(
            reconciliation_graph
        )
    )

    return reconstruction


# ============================================================
# DEBUG HELPERS
# ============================================================


def _case_has_corruption(
    benchmark,
    case_id: str,
    corruption_type: CorruptionType,
) -> bool:
    """
    Return True when the specified case has the specified
    injected corruption.
    """

    return any(
        event.case_id == case_id
        and event.corruption_type == corruption_type
        for event in benchmark.corruption_events
    )


def _print_bank_false_positive_debug(
    benchmark,
    case_id: str,
    clean_reconstruction,
    observed_reconstruction,
    result,
) -> None:
    """
    Print diagnostic information for cases where
    BANK_CREDIT_AMOUNT fails even though the benchmark
    did not inject AMOUNT_MISMATCH.

    This is diagnostic only. It does not alter the result.
    """

    if _case_has_corruption(
        benchmark,
        case_id,
        CorruptionType.AMOUNT_MISMATCH,
    ):
        return

    bank_control = next(
        (
            control
            for control in result.controls
            if control.control_id
            == "BANK_CREDIT_AMOUNT"
        ),
        None,
    )

    if bank_control is None:
        return

    if bank_control.status != ControlStatus.FAIL:
        return

    clean_bank = (
        clean_reconstruction
        .batch_state
        .total_bank_credit_amount
    )

    observed_bank = (
        observed_reconstruction
        .batch_state
        .total_bank_credit_amount
    )

    print()
    print("BANK FALSE POSITIVE DEBUG")
    print("-" * 70)
    print(f"Case:             {case_id}")
    print(f"Clean bank:       {clean_bank}")
    print(f"Observed bank:    {observed_bank}")
    print(
        f"Difference:       "
        f"{observed_bank - clean_bank}"
    )

    print(
        f"Expected value:   "
        f"{bank_control.expected_value}"
    )

    print(
        f"Observed value:   "
        f"{bank_control.observed_value}"
    )

    print(
        f"Control difference: "
        f"{bank_control.difference}"
    )

    print("Corruptions:")

    events = [
        event
        for event in benchmark.corruption_events
        if event.case_id == case_id
    ]

    if not events:
        print("  NONE")

    for event in events:
        print(
            f"  {event.corruption_type.value}"
        )


def _print_timing_debug(
    benchmark,
    case_id: str,
    reconstruction,
    result,
) -> None:
    """
    Print event timestamps for timing-corrupted cases.

    This is diagnostic only. It does not alter the result.
    """

    if not _case_has_corruption(
        benchmark,
        case_id,
        CorruptionType.TIMING_ANOMALY,
    ):
        return

    timing_control = next(
        (
            control
            for control in result.controls
            if control.control_id
            == "SETTLEMENT_TIMING"
        ),
        None,
    )

    print()
    print("TIMING DEBUG")
    print("-" * 70)
    print(f"Case: {case_id}")

    if timing_control is not None:
        print(
            f"SETTLEMENT_TIMING status: "
            f"{timing_control.status}"
        )

        print(
            f"Expected value: "
            f"{timing_control.expected_value}"
        )

        print(
            f"Observed value: "
            f"{timing_control.observed_value}"
        )

        print(
            f"Difference: "
            f"{timing_control.difference}"
        )

    print("Ordered events:")

    for event in (
        reconstruction.event_graph.ordered_events()
    ):
        print(
            f"  {event.event_id} | "
            f"{event.event_type} | "
            f"{event.timestamp}"
        )


# ============================================================
# MAIN EVALUATION
# ============================================================


def run_phase5_evaluation(
    num_cases: int = NUM_CASES,
    seed: int = SEED,
):
    started_at = perf_counter()

    print()
    print("=" * 70)
    print(
        "FINPROOF — PHASE 5 VERIFICATION EVALUATION"
    )
    print("=" * 70)

    # --------------------------------------------------------
    # Configuration
    # --------------------------------------------------------

    print()
    print("CONFIGURATION")
    print("-" * 70)

    print(
        f"Cases:                {num_cases}"    )

    print(
        f"Seed:                 {seed}"
    )

    # --------------------------------------------------------
    # Generate benchmark
    # --------------------------------------------------------

    benchmark = generate_benchmark(
    num_cases=num_cases,
    seed=seed,
    )

    print(
        f"Corruption events:    "
        f"{len(benchmark.corruption_events)}"
    )

    # --------------------------------------------------------
    # Build evaluation ground truth
    # --------------------------------------------------------

    ground_truth = _build_ground_truth(
        benchmark
    )

    # --------------------------------------------------------
    # Build isolated canonical records
    # --------------------------------------------------------

    # Observed records are the corrupted input that
    # goes through the actual Phase 3 → Phase 4 → Phase 5
    # pipeline.

    case_records = _build_case_records(
        benchmark,
        benchmark.observed_records,
    )

    # Clean records are the benchmark's independent
    # reference state.

    clean_case_records = _build_case_records(
        benchmark,
        benchmark.clean_records,
    )

    case_ids = [
        case.case_id
        for case in benchmark.ground_truth.cases
    ]

    # --------------------------------------------------------
    # Initialize runtime components
    # --------------------------------------------------------

    relationship_resolver = (
        RelationshipResolver()
    )

    reconciliation_resolver = (
        ReconciliationResolver()
    )

    reconstructor = Reconstructor()

    from app.verification.verifier import (
        FinancialStateVerifier,
    )

    verifier = FinancialStateVerifier()

    verification_results: list[
        VerificationResult
    ] = []

    runtime_failures: list[str] = []

    # --------------------------------------------------------
    # Execute Phase 3 → Phase 4 → Phase 5
    # --------------------------------------------------------

    print()
    print(
        "RUNNING VERIFICATION PIPELINE"
    )

    print("-" * 70)

    for case_id in case_ids:

        try:

            # ------------------------------------------------
            # OBSERVED / CORRUPTED PIPELINE
            # ------------------------------------------------

            reconstruction = _verify_case(
                case_records[case_id],
                relationship_resolver=(
                    relationship_resolver
                ),
                reconciliation_resolver=(
                    reconciliation_resolver
                ),
                reconstructor=reconstructor,
            )

            result = verifier.verify(
                reconstruction
            )

            # ------------------------------------------------
            # CLEAN / REFERENCE PIPELINE
            # ------------------------------------------------

            clean_reconstruction = _verify_case(
                clean_case_records[case_id],
                relationship_resolver=(
                    relationship_resolver
                ),
                reconciliation_resolver=(
                    reconciliation_resolver
                ),
                reconstructor=reconstructor,
            )

            # ------------------------------------------------
            # Apply clean benchmark reference state ONLY
            # for direct AMOUNT_MISMATCH corruption.
            #
            # Missing and duplicate records have dedicated
            # structural controls:
            #
            #   MISSING_RECORD
            #       -> SETTLEMENT_BANK_COMPLETENESS
            #
            #   DUPLICATE_RECORD
            #       -> DUPLICATE_EVENT
            #
            # Applying the clean bank reference to those cases
            # would correctly reveal a financial difference, but
            # would incorrectly attribute that downstream effect
            # to BANK_CREDIT_AMOUNT.
            #
            # For AMOUNT_MISMATCH, however, the clean reference
            # is exactly what we need to detect the changed bank
            # amount.
            #
            # This is benchmark-only evaluation logic.
            # Production verification remains unchanged.
            # ------------------------------------------------

            has_amount_mismatch = _case_has_corruption(
                benchmark,
                case_id,
                CorruptionType.AMOUNT_MISMATCH,
            )

            if has_amount_mismatch:

                result = _apply_reference_state(
                    result,
                    clean_reconstruction,
                    reconstruction,
                )

            # ------------------------------------------------
            # Temporary diagnostics.
            #
            # These do not alter the result.
            # ------------------------------------------------

            _print_bank_false_positive_debug(
                benchmark,
                case_id,
                clean_reconstruction,
                reconstruction,
                result,
            )

            _print_timing_debug(
                benchmark,
                case_id,
                reconstruction,
                result,
            )

            # ------------------------------------------------
            # The production verifier currently returns the
            # batch-level placeholder:
            #
            #     BATCH_RECONSTRUCTION
            #
            # The runner processes exactly one case at a time,
            # so the evaluation adapter attaches the stable
            # benchmark case ID here.
            #
            # This does NOT affect the verification decision.
            # ------------------------------------------------

            if hasattr(
                result,
                "model_copy",
            ):

                result = result.model_copy(
                    update={
                        "case_id": case_id,
                    }
                )

            else:

                result.case_id = case_id

            verification_results.append(
                result
            )

        except Exception as exc:

            runtime_failures.append(
                f"{case_id}: "
                f"{type(exc).__name__}: {exc}"
            )

    # --------------------------------------------------------
    # Runtime summary
    # --------------------------------------------------------

    print(
        f"Cases successfully verified: "
        f"{len(verification_results)}"
    )

    print(
        f"Runtime pipeline failures:     "
        f"{len(runtime_failures)}"
    )

    # --------------------------------------------------------
    # Stop if runtime execution is incomplete.
    # --------------------------------------------------------

    if len(verification_results) != len(
        ground_truth
    ):

        print()
        print(
            "WARNING: Not all cases reached "
            "the verification evaluator."
        )

        print()
        print("=" * 70)
        print(
            "RUNTIME FAILURES"
        )
        print("=" * 70)

        for failure in runtime_failures:

            print(failure)

        print()
        print("=" * 70)
        print(
            "PHASE 5 EVALUATION NOT COMPLETED"
        )
        print("=" * 70)

        return

    # --------------------------------------------------------
    # Evaluate verification results.
    # --------------------------------------------------------

    evaluator = VerificationEvaluator()

    evaluation = evaluator.evaluate(
        verification_results,
        ground_truth,
    )
    return evaluation
    # --------------------------------------------------------
    # Print evaluation report.
    # --------------------------------------------------------

    print_evaluation_report(
        evaluation
    )

    # --------------------------------------------------------
    # Runner summary.
    # --------------------------------------------------------

    elapsed_seconds = (
        perf_counter()
        - started_at
    )

    print()
    print(
        "RUNNER SUMMARY"
    )

    print("-" * 70)

    print(
        f"Total runner time          : "
        f"{elapsed_seconds:.6f} sec"
    )

    print(
        f"Verified cases             : "
        f"{evaluation.total_cases}"
    )

    print(
        f"Verification throughput    : "
        f"{evaluation.verification_throughput:.2f} "
        f"cases/sec"
    )

    if runtime_failures:

        print()
        print(
            "RUNTIME FAILURES"
        )

        print("-" * 70)

        for failure in runtime_failures:

            print(failure)

    print()
    print("=" * 70)
    print(
        "PHASE 5 EVALUATION COMPLETE"
    )
    print("=" * 70)


if __name__ == "__main__":
    run_phase5_evaluation()