from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from app.application.batch_runtime import save_batch
from app.application.decision_runtime import DecisionRuntime
from app.application.failure_simulation import (
    FailureMode,
    FailureSimulation,
)
from app.application.ingestion import ingest_records
from app.application.models import BatchRuntime, BatchStatus
from app.evidence.graph import EvidenceGraph
from app.evidence.relationship_resolver import RelationshipResolver
from app.investigation.workflow import InvestigationWorkflow
from app.reconciliation.service import ReconciliationService
from app.reconstruction.reconstructor import Reconstructor
from app.verification.verifier import FinancialStateVerifier


@dataclass(frozen=True)
class PipelineRunResult:
    """
    Result of one complete application pipeline execution.
    """

    batch_id: str
    status: BatchStatus
    total_duration_ms: float
    ingestion_duration_ms: float
    reconciliation_duration_ms: float
    reconstruction_duration_ms: float
    verification_duration_ms: float
    investigation_duration_ms: float
    decision_duration_ms: float


class FinProofPipeline:
    """
    Application-level orchestration for the complete FinProof flow.

    Production flow:

        source records
            ↓
        ingestion
            ↓
        EvidenceGraph
            ↓
        reconciliation
            ↓
        reconstruction
            ↓
        verification
            ↓
        investigation
            ↓
        decision

    For backward compatibility with the original Phase 9 tests,
    an already-built EvidenceGraph may also be supplied directly.

    The application pipeline never accepts or uses benchmark
    ground truth.
    """

    def __init__(
        self,
        evidence_resolver: RelationshipResolver | None = None,
        reconciliation_service: ReconciliationService | None = None,
        reconstructor: Reconstructor | None = None,
        verifier: FinancialStateVerifier | None = None,
        investigation_workflow: InvestigationWorkflow | None = None,
        decision_runtime: DecisionRuntime | None = None,
        failure_simulation: FailureSimulation | None = None,
    ) -> None:

        self.evidence_resolver = (
            evidence_resolver
            or RelationshipResolver()
        )

        self.reconciliation_service = (
            reconciliation_service
            or ReconciliationService()
        )

        self.reconstructor = (
            reconstructor
            or Reconstructor()
        )

        self.verifier = (
            verifier
            or FinancialStateVerifier()
        )

        self.investigation_workflow = (
            investigation_workflow
            or InvestigationWorkflow()
        )

        self.decision_runtime = (
            decision_runtime
            or DecisionRuntime()
        )

        self.failure_simulation = (
            failure_simulation
            or FailureSimulation()
        )

    def run(
        self,
        runtime: BatchRuntime,
        records: dict[str, list] | EvidenceGraph,
    ) -> PipelineRunResult:

        batch_id = runtime.metadata.batch_id
        started = perf_counter()

        runtime.metadata = self._set_status(
            runtime,
            BatchStatus.PROCESSING,
        )

        # =========================================================
        # 1. INPUT / INGESTION
        # =========================================================

        ingestion_stage = runtime.stage(
            "ingestion"
        )

        ingestion_stage.status = "RUNNING"

        ingestion_started = perf_counter()

        try:

            if isinstance(records, EvidenceGraph):
                # -------------------------------------------------
                # Backward-compatible path used by existing tests.
                #
                # The caller has already supplied the evidence graph,
                # so no source ingestion is necessary.
                # -------------------------------------------------

                evidence_graph = records

                ingestion_duration_ms = (
                    perf_counter()
                    - ingestion_started
                ) * 1000.0

                ingestion_stage.duration_ms = (
                    ingestion_duration_ms
                )

                ingestion_stage.records_processed = (
                    evidence_graph.node_count
                )

                ingestion_stage.status = "COMPLETED"

                runtime.source_records = {}

            else:
                # -------------------------------------------------
                # Production path.
                #
                # Raw/source records go through the existing
                # ingestion system before relationship resolution.
                # -------------------------------------------------

                ingestion_result = ingest_records(
                    records
                )

                ingestion_duration_ms = (
                    perf_counter()
                    - ingestion_started
                ) * 1000.0

                ingestion_stage.duration_ms = (
                    ingestion_duration_ms
                )

                ingestion_stage.records_processed = (
                    ingestion_result.total_records
                )

                ingestion_stage.status = "COMPLETED"

                runtime.source_records = records

                # -------------------------------------------------
                # Existing evidence relationship resolver.
                # -------------------------------------------------

                evidence_graph = (
                    self.evidence_resolver.resolve(
                        ingestion_result
                    )
                )

            runtime.evidence_graph = evidence_graph

        except Exception as exc:

            ingestion_stage.status = "FAILED"
            ingestion_stage.error = str(exc)

            runtime.metadata = self._set_status(
                runtime,
                BatchStatus.FAILED,
            )

            save_batch(runtime)

            raise

        # =========================================================
        # 2. EVIDENCE VALIDATION
        # =========================================================

        evidence_stage = runtime.stage(
            "evidence_validation"
        )

        evidence_stage.status = "RUNNING"

        evidence_started = perf_counter()

        try:

            # EvidenceGraph construction/relationship resolution has
            # already happened above. This stage records the runtime
            # observability boundary without modifying evidence.

            evidence_duration_ms = (
                perf_counter()
                - evidence_started
            ) * 1000.0

            evidence_stage.duration_ms = (
                evidence_duration_ms
            )

            evidence_stage.records_processed = (
                evidence_graph.node_count
            )

            evidence_stage.status = "COMPLETED"

        except Exception as exc:

            evidence_stage.status = "FAILED"
            evidence_stage.error = str(exc)

            runtime.metadata = self._set_status(
                runtime,
                BatchStatus.FAILED,
            )

            save_batch(runtime)

            raise

        # =========================================================
        # 3. RECONCILIATION
        # =========================================================

        reconciliation_stage = runtime.stage(
            "reconciliation"
        )

        reconciliation_stage.status = "RUNNING"

        reconciliation_started = perf_counter()

        try:

            reconciliation_result = (
                self.reconciliation_service.reconcile(
                    evidence_graph
                )
            )

            reconciliation_duration_ms = (
                perf_counter()
                - reconciliation_started
            ) * 1000.0

            reconciliation_stage.duration_ms = (
                reconciliation_duration_ms
            )

            reconciliation_stage.records_processed = (
                reconciliation_result.node_count
            )

            reconciliation_stage.status = "COMPLETED"

            runtime.reconciliation_result = (
                reconciliation_result
            )

        except Exception as exc:

            reconciliation_stage.status = "FAILED"
            reconciliation_stage.error = str(exc)

            runtime.metadata = self._set_status(
                runtime,
                BatchStatus.FAILED,
            )

            save_batch(runtime)

            raise

        # =========================================================
        # 4. RECONSTRUCTION
        # =========================================================

        reconstruction_stage = runtime.stage(
            "reconstruction"
        )

        reconstruction_stage.status = "RUNNING"

        reconstruction_started = perf_counter()

        try:

            reconstruction_result = (
                self.reconstructor.reconstruct(
                    reconciliation_result.graph
                )
            )

            reconstruction_duration_ms = (
                perf_counter()
                - reconstruction_started
            ) * 1000.0

            reconstruction_stage.duration_ms = (
                reconstruction_duration_ms
            )

            reconstruction_stage.records_processed = (
                reconstruction_result.event_graph.node_count
            )

            reconstruction_stage.status = "COMPLETED"

            runtime.reconstruction_result = (
                reconstruction_result
            )

        except Exception as exc:

            reconstruction_stage.status = "FAILED"
            reconstruction_stage.error = str(exc)

            runtime.metadata = self._set_status(
                runtime,
                BatchStatus.FAILED,
            )

            save_batch(runtime)

            raise

        # =========================================================
        # 5. VERIFICATION
        # =========================================================

        verification_stage = runtime.stage(
            "verification"
        )

        verification_stage.status = "RUNNING"

        verification_started = perf_counter()

        try:

            verification_result = (
                self.verifier.verify(
                    reconstruction_result
                )
            )

            verification_duration_ms = (
                perf_counter()
                - verification_started
            ) * 1000.0

            verification_stage.duration_ms = (
                verification_duration_ms
            )

            verification_stage.records_processed = len(
                getattr(
                    verification_result,
                    "controls",
                    (),
                )
            )

            verification_stage.status = "COMPLETED"

            runtime.verification_result = (
                verification_result
            )

        except Exception as exc:

            verification_stage.status = "FAILED"
            verification_stage.error = str(exc)

            runtime.metadata = self._set_status(
                runtime,
                BatchStatus.FAILED,
            )

            save_batch(runtime)

            raise

        # =========================================================
        # 6. INVESTIGATION
        # =========================================================

        investigation_stage = runtime.stage(
            "investigation"
        )

        investigation_stage.status = "RUNNING"

        investigation_started = perf_counter()

        try:

            if (
                self.failure_simulation.mode
                == FailureMode.AI_UNAVAILABLE
            ):
                # Controlled Phase 9 failure simulation:
                # deterministic verification has already completed.
                # The investigation layer is intentionally unavailable,
                # so no unsupported AI explanation is produced.
                investigation_result = None

                investigation_duration_ms = (
                    perf_counter()
                    - investigation_started
                ) * 1000.0

                investigation_stage.duration_ms = (
                    investigation_duration_ms
                )

                investigation_stage.records_processed = 0
                investigation_stage.status = "UNAVAILABLE"
                investigation_stage.error = (
                    "Simulated AI unavailable"
                )

            else:
                investigation_result = (
                    self.investigation_workflow.investigate(
                        verification_result,
                        reconstruction_result.event_graph,
                    )
                )

                investigation_duration_ms = (
                perf_counter()
                - investigation_started
            ) * 1000.0

                investigation_stage.duration_ms = (
                    investigation_duration_ms
                )

                investigation_stage.records_processed = (
                    investigation_result.count
                )

                investigation_stage.status = "COMPLETED"

            runtime.investigation_result = investigation_result

        except Exception as exc:

            investigation_stage.status = "FAILED"
            investigation_stage.error = str(exc)

            runtime.metadata = self._set_status(
                runtime,
                BatchStatus.FAILED,
            )

            save_batch(runtime)

            raise

        # =========================================================
        # 7. DECISION
        # =========================================================

        decision_stage = runtime.stage(
            "decision"
        )

        decision_stage.status = "RUNNING"

        decision_started = perf_counter()

        try:

            if runtime.investigation_result is None:
                # Investigation is unavailable (for example, when the
                # AI_UNAVAILABLE failure mode is active). The decision
                # layer must still receive the verified financial state,
                # but it must not be given fabricated investigation data.
                investigation_results = ()
            else:
                investigation_results = tuple(
                    runtime.investigation_result.investigation_results
                )

            decision_result = (
                self.decision_runtime.decide(
                    batch_id=batch_id,
                    verification=verification_result,
                    investigations=investigation_results,
                )
            )

            decision_duration_ms = (
                perf_counter()
                - decision_started
            ) * 1000.0

            decision_stage.duration_ms = (
                decision_duration_ms
            )

            decision_stage.records_processed = (
                len(
                    decision_result.decisions
                )
            )

            decision_stage.status = "COMPLETED"

            if investigation_results:
                runtime.decisions = {
                    investigation.case_id: decision
                    for investigation, decision in zip(
                        investigation_results,
                        decision_result.decisions,
                    )
                 }
            else:
                runtime.decisions = {
                    verification_result.case_id: decision
                    for decision in decision_result.decisions
            }

        except Exception as exc:

            decision_stage.status = "FAILED"
            decision_stage.error = str(exc)

            runtime.metadata = self._set_status(
                runtime,
                BatchStatus.FAILED,
            )

            save_batch(runtime)

            raise

        # =========================================================
        # COMPLETE
        # =========================================================

        total_duration_ms = (
            perf_counter()
            - started
        ) * 1000.0

        runtime.metadata = self._set_status(
            runtime,
            BatchStatus.COMPLETED,
        )

        save_batch(runtime)

        return PipelineRunResult(
            batch_id=batch_id,
            status=BatchStatus.COMPLETED,
            total_duration_ms=total_duration_ms,
            ingestion_duration_ms=(
                ingestion_duration_ms
            ),
            reconciliation_duration_ms=(
                reconciliation_duration_ms
            ),
            reconstruction_duration_ms=(
                reconstruction_duration_ms
            ),
            verification_duration_ms=(
                verification_duration_ms
            ),
            investigation_duration_ms=(
                investigation_duration_ms
            ),
            decision_duration_ms=(
                decision_duration_ms
            ),
        )

    @staticmethod
    def _set_status(
        runtime: BatchRuntime,
        status: BatchStatus,
    ):
        metadata = runtime.metadata

        runtime.metadata = type(metadata)(
            batch_id=metadata.batch_id,
            name=metadata.name,
            scenario=metadata.scenario,
            seed=metadata.seed,
            status=status,
        )

        return runtime.metadata