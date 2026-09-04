from decimal import Decimal
from time import perf_counter

from app.domain.enums import EventType
from app.domain.graph import EventGraph
from app.reconstruction.result import ReconstructionResult
from app.verification.completeness import (
    run_completeness_controls,
)
from app.verification.discrepancy import DiscrepancyBuilder
from app.verification.expected_state import (
    ExpectedStateCalculator,
)
from app.verification.invariants import run_invariants
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    VerificationResult,
    VerificationStatus,
)
from app.verification.temporal import (
    run_temporal_controls,
)
from app.verification.duplicates import (
    run_duplicate_controls,
)
from app.verification.currency import (
    run_currency_controls,
)


class FinancialStateVerifier:
    """
    Phase 5 financial state verification engine.

    The verifier consumes the reconstructed state produced
    by Phase 4.

    It independently calculates the expected financial state,
    executes deterministic controls, and converts failed controls
    into structured discrepancies.

    It does not:
        - modify reconstructed evidence
        - create events
        - repair records
        - infer root causes
        - perform investigation
        - use an LLM
    """

    def __init__(
        self,
        expected_state_calculator: ExpectedStateCalculator | None = None,
        discrepancy_builder: DiscrepancyBuilder | None = None,
    ):
        self.expected_state_calculator = (
            expected_state_calculator
            or ExpectedStateCalculator()
        )

        self.discrepancy_builder = (
            discrepancy_builder
            or DiscrepancyBuilder()
        )

    def verify(
        self,
        reconstruction: ReconstructionResult,
    ) -> VerificationResult:
        """
        Verify one Phase 4 reconstruction result.
        """

        started_at = perf_counter()

        batch_state = reconstruction.batch_state

        # --------------------------------------------------------
        # STEP 1 — Calculate independent expected financial state
        # --------------------------------------------------------

        expected_state = (
            self.expected_state_calculator.calculate(
                batch_state
            )
        )

        # --------------------------------------------------------
        # STEP 2 — Obtain event graph
        #
        # Older aggregate fixtures may not contain an event graph.
        # In that case, use an empty graph rather than fabricating
        # financial events.
        # --------------------------------------------------------

        event_graph = (
            reconstruction.event_graph
            if reconstruction.event_graph is not None
            else EventGraph()
        )

        # --------------------------------------------------------
        # STEP 3 — Run amount/accounting controls
        # --------------------------------------------------------

        controls = run_invariants(
            expected_state,
            batch_state,
        )

        # --------------------------------------------------------
        # STEP 3.1 — Preserve event provenance for amount controls
        #
        # Aggregate amount controls operate on BatchReconstructionState
        # and therefore do not know which reconstructed events supplied
        # the observed amount.
        #
        # The verifier has access to the EventGraph, so it can attach
        # observable event provenance without changing the financial
        # calculation or control result.
        # --------------------------------------------------------

        controls = self._attach_control_provenance(
            controls,
            event_graph,
        )

        # --------------------------------------------------------
        # STEP 4 — Run temporal/lifecycle controls
        # --------------------------------------------------------

        temporal_controls = run_temporal_controls(
            event_graph,
            list(reconstruction.chains),
        )

        controls.extend(
            temporal_controls
        )

        # --------------------------------------------------------
        # STEP 5 — Run completeness controls
        # --------------------------------------------------------

        completeness_controls = (
            run_completeness_controls(
                event_graph
            )
        )

        controls.extend(
            completeness_controls
        )

        # --------------------------------------------------------
        # STEP 5.2 — Run duplicate-protection controls
        # --------------------------------------------------------

        duplicate_controls = run_duplicate_controls(
            event_graph
        )

        controls.extend(
            duplicate_controls
        )

        # --------------------------------------------------------
        # STEP 5.3 — Run currency-consistency controls
        # --------------------------------------------------------

        currency_controls = run_currency_controls(
            event_graph
        )

        controls.extend(
            currency_controls
        )

        # --------------------------------------------------------
        # STEP 6 — Convert failed controls into discrepancies
        # --------------------------------------------------------

        discrepancies = []

        for control in controls:

            discrepancy = (
                self.discrepancy_builder.build(
                    control
                )
            )

            if discrepancy is not None:
                discrepancies.append(
                    discrepancy
                )

        # --------------------------------------------------------
        # STEP 7 — Determine overall verification status
        # --------------------------------------------------------

        status = self._determine_status(
            controls,
            discrepancies,
        )

        # --------------------------------------------------------
        # STEP 8 — Measure processing time
        # --------------------------------------------------------

        elapsed_ms = Decimal(
            str(
                (perf_counter() - started_at)
                * 1000
            )
        )

        # --------------------------------------------------------
        # STEP 9 — Preserve observed state
        # --------------------------------------------------------

        observed_state = {
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
            "total_settled": (
                batch_state.total_settlement_amount
            ),
            "total_bank_credited": (
                batch_state.total_bank_credit_amount
            ),
        }

        # --------------------------------------------------------
        # STEP 10 — Return complete verification result
        # --------------------------------------------------------

        return VerificationResult(
            case_id=self._case_id(
                reconstruction
            ),
            status=status,
            observed_state=observed_state,
            expected_state=expected_state,
            controls=controls,
            discrepancies=discrepancies,
            processing_time_ms=elapsed_ms,
        )

    @staticmethod
    def _attach_control_provenance(
        controls: list[ControlCheck],
        event_graph: EventGraph,
    ) -> list[ControlCheck]:
        """
        Attach observable event provenance to failed aggregate
        amount controls.

        Amount invariants operate on aggregate reconstructed state
        and therefore cannot identify their source events directly.

        The verifier already has the Phase 4 EventGraph, so it
        enriches the failed control with the corresponding observable
        event IDs.

        This method does not:
            - change control status
            - change expected values
            - change observed values
            - change differences
            - infer root causes
            - create events
            - modify the EventGraph
        """

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

        enriched_controls: list[ControlCheck] = []

        for control in controls:

            if (
                control.status != ControlStatus.FAIL
                or control.affected_event_ids
            ):
                enriched_controls.append(
                    control
                )
                continue

            event_types = control_event_types.get(
                control.control_id
            )

            if not event_types:
                enriched_controls.append(
                    control
                )
                continue

            affected_event_ids = [
                event.event_id
                for event in event_graph.events.values()
                if event.event_type in event_types
            ]

            if not affected_event_ids:
                enriched_controls.append(
                    control
                )
                continue

            enriched_controls.append(
                control.model_copy(
                    update={
                        "affected_event_ids": (
                            affected_event_ids
                        )
                    }
                )
            )

        return enriched_controls

    @staticmethod
    def _determine_status(
        controls,
        discrepancies,
    ) -> VerificationStatus:
        """
        Determine the overall verification status.

        FAIL:
            At least one deterministic control failed.

        VERIFIED:
            At least one applicable control passed and
            no control failed.

        PENDING:
            No applicable control produced a decisive result.

        INDETERMINATE:
            Reserved for future cases where the verification
            state cannot be classified deterministically.
        """

        if any(
            control.status == ControlStatus.FAIL
            for control in controls
        ):
            return VerificationStatus.FAILED

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
            return VerificationStatus.VERIFIED

        return VerificationStatus.PENDING

    @staticmethod
    def _case_id(
        reconstruction: ReconstructionResult,
    ) -> str:
        """
        Obtain a stable identifier for the current
        batch-level reconstruction.

        Phase 4's current aggregate ReconstructionResult
        does not carry a case_id.
        """

        return "BATCH_RECONSTRUCTION"


def verify_reconstruction(
    reconstruction: ReconstructionResult,
) -> VerificationResult:
    """
    Convenience function for verifying a reconstruction.
    """

    return FinancialStateVerifier().verify(
        reconstruction
    )