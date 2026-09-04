from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException

from app.reconstruction.result import ReconstructionResult
from app.verification.models import VerificationResult
from app.verification.verifier import FinancialStateVerifier


@dataclass
class VerificationBatchStore:
    """
    In-memory store for Phase 5 verification inputs
    and results.

    This store contains reconstructed runtime state only.
    Ground truth is never stored here.
    """

    reconstructions: dict[
        str,
        ReconstructionResult,
    ] = field(default_factory=dict)

    results: dict[
        str,
        VerificationResult,
    ] = field(default_factory=dict)

    def register(
        self,
        batch_id: str,
        reconstruction: ReconstructionResult,
    ) -> None:
        self.reconstructions[batch_id] = reconstruction

    def get_reconstruction(
        self,
        batch_id: str,
    ) -> ReconstructionResult:

        reconstruction = self.reconstructions.get(
            batch_id
        )

        if reconstruction is None:
            raise KeyError(
                f"Reconstruction not found: {batch_id}"
            )

        return reconstruction

    def save_result(
        self,
        batch_id: str,
        result: VerificationResult,
    ) -> None:
        self.results[batch_id] = result

    def get_result(
        self,
        batch_id: str,
    ) -> VerificationResult:

        result = self.results.get(batch_id)

        if result is None:
            raise KeyError(
                f"Verification not found: {batch_id}"
            )

        return result

    def clear(self) -> None:
        self.reconstructions.clear()
        self.results.clear()


store = VerificationBatchStore()

router = APIRouter(
    prefix="",
    tags=["verification"],
)

verifier = FinancialStateVerifier()


def _get_reconstruction(
    batch_id: str,
) -> ReconstructionResult:

    try:
        return store.get_reconstruction(
            batch_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


def _get_result(
    batch_id: str,
) -> VerificationResult:

    try:
        return store.get_result(
            batch_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


def _serialize_decimal(
    value,
) -> str | None:

    if value is None:
        return None

    return str(value)


def _serialize_expected_state(
    state,
) -> dict[str, Any]:

    return {
        "gross_captured": _serialize_decimal(
            state.gross_captured
        ),
        "total_refunded": _serialize_decimal(
            state.total_refunded
        ),
        "total_fees": _serialize_decimal(
            state.total_fees
        ),
        "total_tax": _serialize_decimal(
            state.total_tax
        ),
        "total_adjustments": _serialize_decimal(
            state.total_adjustments
        ),
        "expected_settlement": _serialize_decimal(
            state.expected_settlement
        ),
        "expected_bank_credit": _serialize_decimal(
            state.expected_bank_credit
        ),
        "expected_event_states": dict(
            state.expected_event_states
        ),
    }


def _serialize_control(
    control,
) -> dict[str, Any]:

    return {
        "control_id": control.control_id,
        "control_name": control.control_name,
        "status": control.status.value,
        "expected_value": _serialize_decimal(
            control.expected_value
        ),
        "observed_value": _serialize_decimal(
            control.observed_value
        ),
        "difference": _serialize_decimal(
            control.difference
        ),
        "affected_event_ids": list(
            control.affected_event_ids
        ),
        "supporting_evidence_ids": list(
            control.supporting_evidence_ids
        ),
        "severity": control.severity.value,
        "blocking": control.blocking,
    }


def _serialize_discrepancy(
    discrepancy,
) -> dict[str, Any]:

    return {
        "discrepancy_id": discrepancy.discrepancy_id,
        "control_id": discrepancy.control_id,
        "expected_value": _serialize_decimal(
            discrepancy.expected_value
        ),
        "observed_value": _serialize_decimal(
            discrepancy.observed_value
        ),
        "difference": _serialize_decimal(
            discrepancy.difference
        ),
        "relative_difference": _serialize_decimal(
            discrepancy.relative_difference
        ),
        "affected_event_ids": list(
            discrepancy.affected_event_ids
        ),
        "evidence_references": list(
            discrepancy.evidence_references
        ),
        "materiality": discrepancy.materiality.value,
        "blocking": discrepancy.blocking,
        "investigation_status": (
            discrepancy.investigation_status.value
        ),
    }


def _serialize_result(
    batch_id: str,
    result: VerificationResult,
) -> dict[str, Any]:

    return {
        "batch_id": batch_id,
        "case_id": result.case_id,
        "status": result.status.value,
        "observed_state": {
            key: str(value)
            for key, value
            in result.observed_state.items()
        },
        "expected_state": _serialize_expected_state(
            result.expected_state
        ),
        "controls": [
            _serialize_control(control)
            for control in result.controls
        ],
        "discrepancies": [
            _serialize_discrepancy(discrepancy)
            for discrepancy
            in result.discrepancies
        ],
        "processing_time_ms": _serialize_decimal(
            result.processing_time_ms
        ),
    }


@router.post(
    "/batches/{batch_id}/verify"
)
def verify_batch(
    batch_id: str,
) -> dict[str, Any]:

    reconstruction = _get_reconstruction(
        batch_id
    )

    result = verifier.verify(
        reconstruction
    )

    store.save_result(
        batch_id,
        result,
    )

    return _serialize_result(
        batch_id,
        result,
    )


@router.get(
    "/batches/{batch_id}/verification"
)
def get_verification(
    batch_id: str,
) -> dict[str, Any]:

    result = _get_result(
        batch_id
    )

    return _serialize_result(
        batch_id,
        result,
    )


@router.get(
    "/verification/{case_id}/discrepancies"
)
def get_discrepancies(
    case_id: str,
) -> dict[str, Any]:

    for result in store.results.values():

        if result.case_id != case_id:
            continue

        return {
            "case_id": case_id,
            "count": len(
                result.discrepancies
            ),
            "items": [
                _serialize_discrepancy(
                    discrepancy
                )
                for discrepancy
                in result.discrepancies
            ],
        }

    raise HTTPException(
        status_code=404,
        detail=(
            "Verification not found for case: "
            f"{case_id}"
        ),
    )