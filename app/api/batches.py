from __future__ import annotations
from app.application.demo_scenarios import apply_demo_scenario
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.application.batch_runtime import (
    get_batch,
    register_batch,
)
from app.application.ingestion import (
    generate_demo_records,
)
from app.application.failure_simulation import (
    FailureMode,
    create_failure_simulation,
)
from app.application.pipeline import (
    FinProofPipeline,
)

from app.api.reconciliation import (
    _serialize_metrics,
    _serialize_relationship,
    _serialize_review_item,
)

from app.api.verification import (
    _serialize_result as _serialize_verification_result_detail,
)


router = APIRouter(
    prefix="",
    tags=["batches"],
)


# Keep this module-level object because existing tests import it.
#
# Actual batch execution intentionally creates a fresh pipeline
# instance inside run_batch() to avoid state leakage between
# deterministic batches.
pipeline = FinProofPipeline()

# Failure simulation configuration is batch-scoped and in-memory,
# matching the existing BatchRuntimeStore lifecycle.
_batch_failure_modes: dict[str, FailureMode] = {}


# ============================================================
# REQUEST MODELS
# ============================================================


class CreateBatchRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=200,
    )

    scenario: str = Field(
        default="NORMAL",
        min_length=1,
        max_length=50,
    )

    seed: int = Field(
        default=42,
        ge=0,
    )

    num_cases: int = Field(
        default=100,
        ge=1,
        le=1000,
    )

    failure_mode: str = Field(
        default="NONE",
        min_length=1,
        max_length=80,
    )


# ============================================================
# HELPERS
# ============================================================


_ALLOWED_SCENARIOS = {
    "NORMAL",
    "MIXED",
    "ADVERSARIAL",
    "FAILURE_HEAVY",
}


def _normalize_scenario(
    scenario: str,
) -> str:
    normalized = scenario.strip().upper()

    if normalized not in _ALLOWED_SCENARIOS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unsupported scenario. "
                "Expected one of: "
                + ", ".join(
                    sorted(_ALLOWED_SCENARIOS)
                )
            ),
        )

    return normalized


def _normalize_failure_mode(
    failure_mode: str,
) -> FailureMode:
    try:
        return create_failure_simulation(
            failure_mode
        ).mode
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc


def _serialize_stage(stage) -> dict[str, Any]:
    return {
        "name": stage.name,
        "status": stage.status,
        "duration_ms": stage.duration_ms,
        "records_processed": stage.records_processed,
        "error": stage.error,
    }


def _serialize_batch(runtime) -> dict[str, Any]:
    return {
        "batch_id": runtime.metadata.batch_id,
        "name": runtime.metadata.name,
        "scenario": runtime.metadata.scenario,
        "seed": runtime.metadata.seed,
        "status": runtime.metadata.status.value,
        "failure_mode": _batch_failure_modes.get(
            runtime.metadata.batch_id,
            FailureMode.NONE,
        ).value,
        "created_at": runtime.created_at,
        "completed_at": runtime.completed_at,
        "case_count": runtime.case_count,
        "financial_impact": str(
            runtime.financial_impact
        ),
        "stages": [
            _serialize_stage(stage)
            for stage in runtime.stages
        ],
    }


def _get_runtime(batch_id: str):
    try:
        return get_batch(batch_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


def _serialize_reconciliation_projection(
    result,
) -> dict[str, Any]:
    if result is None:
        return {
            "available": False,
            "node_count": 0,
            "relationship_count": 0,
            "relationships": [],
            "review_items": [],
            "metrics": None,
        }

    return {
        "available": True,
        "node_count": result.node_count,
        "relationship_count": result.relationship_count,
        "relationships": [
            _serialize_relationship(
                relationship
            )
            for relationship in result.relationships
        ],
        "review_items": [
            _serialize_review_item(
                item
            )
            for item in result.review_items
        ],
        "metrics": _serialize_metrics(
            result.metrics
        ),
    }


def _serialize_reconstruction_projection(
    result,
) -> dict[str, Any]:
    if result is None:
        return {
            "available": False,
            "event_count": 0,
            "relationship_count": 0,
            "chain_count": 0,
            "has_events": False,
            "has_relationships": False,
            "chains": [],
        }

    return {
        "available": True,
        "event_count": result.event_count,
        "relationship_count": result.relationship_count,
        "chain_count": result.chain_count,
        "has_events": result.has_events,
        "has_relationships": result.has_relationships,
        "chains": [
            {
                "chain_id": chain.chain_id,
                "event_ids": list(chain.event_ids),
                "length": chain.length,
                "first_event_id": chain.first_event_id,
                "last_event_id": chain.last_event_id,
            }
            for chain in result.chains
        ],
    }

def _serialize_verification_projection(
    batch_id: str,
    result,
) -> dict[str, Any]:
    if result is None:
        return {
            "available": False,
            "case_id": None,
            "status": None,
            "expected_state": None,
            "observed_state": {},
            "controls": [],
            "discrepancies": [],
            "processing_time_ms": None,
        }

    # Reuse the authoritative Phase 5 API serializer.
    serialized = _serialize_verification_result_detail(
        batch_id,
        result,
    )

    return {
        "available": True,
        **serialized,
    }


def _decision_outcome_value(
    decision_result,
) -> str | None:
    if decision_result is None:
        return None

    decision = getattr(
        decision_result,
        "decision",
        None,
    )

    if decision is None:
        return None

    outcome = getattr(
        decision,
        "outcome",
        None,
    )

    if outcome is None:
        return None

    return getattr(
        outcome,
        "value",
        str(outcome),
    )


def _serialize_control_projection(
    runtime,
) -> dict[str, Any]:

    verification = runtime.verification_result

    if verification is None:
        return {
            "available": False,
            "status": None,
            "case_count": 0,
            "discrepancy_count": 0,
            "financial_impact": "0",
            "controls": [],
            "decisions": [],
        }

    controls = [
        {
            "control_id": control.control_id,
            "control_name": control.control_name,
            "status": control.status.value,
            "severity": control.severity.value,
            "blocking": control.blocking,
            "expected_value": (
                None
                if control.expected_value is None
                else str(control.expected_value)
            ),
            "observed_value": (
                None
                if control.observed_value is None
                else str(control.observed_value)
            ),
            "difference": (
                None
                if control.difference is None
                else str(control.difference)
            ),
            "affected_event_ids": list(
                control.affected_event_ids
            ),
            "supporting_evidence_ids": list(
                control.supporting_evidence_ids
            ),
        }
        for control in verification.controls
    ]

    discrepancies = list(
        verification.discrepancies
    )

    decisions = [
        {
            "case_id": case_id,
            "outcome": _decision_outcome_value(
                decision_result
            ),
        }
        for case_id, decision_result
        in runtime.decisions.items()
    ]

    # Prefer the Phase 7 decision when available.
    decision_outcomes = [
        item["outcome"]
        for item in decisions
        if item["outcome"] is not None
    ]

    if decision_outcomes:
        # A batch-level dashboard should surface the most
        # conservative outcome when several outcomes exist.
        priority = {
            "BLOCKED": 5,
            "HUMAN_REVIEW": 4,
            "RESOLVED_WITH_APPROVAL": 3,
            "PENDING": 2,
            "AUTO_RESOLVED": 1,
        }

        status = max(
            decision_outcomes,
            key=lambda value: priority.get(
                value,
                0,
            ),
        )
    else:
        status = verification.status.value

    financial_impact = sum(
        (
            abs(
                discrepancy.difference
            )
            for discrepancy in discrepancies
        ),
        start=0,
    )

    return {
        "available": True,
        "status": status,
        "verification_status": (
            verification.status.value
        ),
        "case_count": 1,
        "discrepancy_count": len(
            discrepancies
        ),
        "financial_impact": str(
            financial_impact
        ),
        "controls": controls,
        "decisions": decisions,
    }


# ============================================================
# BATCH CREATION
# ============================================================


@router.post(
    "/batches",
)
def create_batch(
    request: CreateBatchRequest,
) -> dict[str, Any]:

    scenario = _normalize_scenario(
        request.scenario
    )

    failure_mode = _normalize_failure_mode(
        request.failure_mode
    )

    batch_id = (
    f"batch-{scenario.lower()}-"
    f"{request.seed}-"
    f"{request.num_cases}-"
    f"{len(request.name)}"
)
    # Avoid accidental collision when the same demo request
    # is submitted more than once.
    existing = None

    try:
        existing = get_batch(batch_id)
    except KeyError:
        pass

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Batch already exists: {batch_id}",
        )

    runtime = register_batch(
        batch_id=batch_id,
        name=request.name,
        scenario=scenario,
        seed=request.seed,
    )

    _batch_failure_modes[batch_id] = failure_mode

    records = generate_demo_records(
        num_cases=request.num_cases,
        seed=request.seed,
    )

    runtime.source_records = apply_demo_scenario(
        records,
        scenario,
    )

    return _serialize_batch(
        runtime
    )


# ============================================================
# BATCH EXECUTION
# ============================================================


@router.post(
    "/batches/{batch_id}/run",
)
def run_batch(
    batch_id: str,
) -> dict[str, Any]:

    runtime = _get_runtime(
        batch_id
    )

    if runtime.metadata.status.value == "COMPLETED":
        return {
            "batch": _serialize_batch(
                runtime
            ),
            "message": "Batch already completed.",
        }

    if runtime.metadata.status.value == "PROCESSING":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Batch is already processing: "
                f"{batch_id}"
            ),
        )

    if not runtime.source_records:
        raise HTTPException(
            status_code=422,
            detail=(
                "Batch has no source records: "
                f"{batch_id}"
            ),
        )

    try:
        # Fresh pipeline instance per batch.
        #
        # DecisionService is stateful, so sharing one instance
        # across deterministic batches can leak case state.
        failure_simulation = create_failure_simulation(
            _batch_failure_modes.get(
                batch_id,
                FailureMode.NONE,
            )
        )

        result = FinProofPipeline(
            failure_simulation=failure_simulation,
        ).run(
            runtime,
            runtime.source_records,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "PIPELINE_FAILURE",
                "message": str(exc),
                "batch_id": batch_id,
            },
        ) from exc

    return {
        "batch": _serialize_batch(
            runtime
        ),
        "pipeline": {
            "batch_id": result.batch_id,
            "status": result.status.value,
            "total_duration_ms": (
                result.total_duration_ms
            ),
            "ingestion_duration_ms": (
                result.ingestion_duration_ms
            ),
            "reconciliation_duration_ms": (
                result.reconciliation_duration_ms
            ),
            "reconstruction_duration_ms": (
                result.reconstruction_duration_ms
            ),
            "verification_duration_ms": (
                result.verification_duration_ms
            ),
            "investigation_duration_ms": (
                result.investigation_duration_ms
            ),
            "decision_duration_ms": (
                result.decision_duration_ms
            ),
        },
    }


# ============================================================
# BATCH DETAILS
# ============================================================


@router.get(
    "/batches/{batch_id}",
)
def get_batch_details(
    batch_id: str,
) -> dict[str, Any]:

    runtime = _get_runtime(
        batch_id
    )

    return _serialize_batch(
        runtime
    )


# ============================================================
# INGESTION REPORT
# ============================================================


@router.get(
    "/batches/{batch_id}/ingestion-report",
)
def get_ingestion_report(
    batch_id: str,
) -> dict[str, Any]:

    runtime = _get_runtime(
        batch_id
    )

    records = runtime.source_records

    if not records:
        return {
            "batch_id": batch_id,
            "available": False,
            "records": {},
            "total_records": 0,
        }

    counts = {
        source: len(
            records.get(source, [])
        )
        for source in (
            "orders",
            "payments",
            "refunds",
            "fees",
            "adjustments",
            "settlements",
            "bank",
        )
    }

    return {
        "batch_id": batch_id,
        "available": True,
        "records": counts,
        "total_records": sum(
            counts.values()
        ),
        "ingestion_stage": (
            _serialize_stage(
                runtime.stage("ingestion")
            )
        ),
    }





# ============================================================
# PHASE 4 — RECONSTRUCTION PROJECTION
# ============================================================


@router.get(
    "/batches/{batch_id}/reconstruction",
)
def get_batch_reconstruction(
    batch_id: str,
) -> dict[str, Any]:

    runtime = _get_runtime(
        batch_id
    )

    return {
        "batch_id": batch_id,
        **_serialize_reconstruction_projection(
            runtime.reconstruction_result
        ),
    }


# ============================================================
# PHASE 5 — VERIFICATION PROJECTION
# ============================================================


@router.get(
    "/batches/{batch_id}/verification",
)
def get_batch_verification(
    batch_id: str,
) -> dict[str, Any]:

    runtime = _get_runtime(
        batch_id
    )

    return {
        "batch_id": batch_id,
        **_serialize_verification_projection(
            batch_id,
            runtime.verification_result,
        ),
    }


