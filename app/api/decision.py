from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.decisions.batch_controller import (
    BatchDecisionController,
)
from app.decisions.models import (
    DecisionOutcome,
    ReviewAction,
)
from app.decisions.service import (
    DecisionService,
    DecisionServiceResult,
)
from app.investigation.models import (
    InvestigationResult,
)
from app.verification.models import (
    VerificationResult,
)


router = APIRouter(
    prefix="",
    tags=["decisions"],
)


service = DecisionService()
batch_controller = BatchDecisionController()


# ============================================================
# IN-MEMORY CASE STORE
# ============================================================


class DecisionCaseStore:
    """
    In-memory Phase 7 case store.

    Stores runtime verification/investigation inputs and
    resulting Phase 7 decisions.

    Batch membership is explicit. A decision is never assumed
    to belong to every batch.
    """

    def __init__(self) -> None:
        self.verifications: dict[
            str,
            VerificationResult,
        ] = {}

        self.investigations: dict[
            str,
            InvestigationResult,
        ] = {}

        self.results: dict[
            str,
            DecisionServiceResult,
        ] = {}

        self.batches: dict[
            str,
            set[str],
        ] = {}

    def register_verification(
        self,
        verification: VerificationResult,
    ) -> None:
        self.verifications[
            verification.case_id
        ] = verification

    def register_investigation(
        self,
        investigation: InvestigationResult,
    ) -> None:
        self.investigations[
            investigation.case_id
        ] = investigation

    def get_verification(
        self,
        case_id: str,
    ) -> VerificationResult:
        result = self.verifications.get(
            case_id
        )

        if result is None:
            raise KeyError(
                f"Verification not found: {case_id}"
            )

        return result

    def get_investigation(
        self,
        case_id: str,
    ) -> InvestigationResult | None:
        return self.investigations.get(
            case_id
        )

    def save_result(
        self,
        case_id: str,
        result: DecisionServiceResult,
        batch_id: str | None = None,
    ) -> None:
        self.results[case_id] = result

        if batch_id is not None:
            self.batches.setdefault(
                batch_id,
                set(),
            ).add(case_id)

    def register_case_to_batch(
        self,
        batch_id: str,
        case_id: str,
    ) -> None:
        if case_id not in self.results:
            raise KeyError(
                f"Decision not found: {case_id}"
            )

        self.batches.setdefault(
            batch_id,
            set(),
        ).add(case_id)

    def get_result(
        self,
        case_id: str,
    ) -> DecisionServiceResult:
        result = self.results.get(
            case_id
        )

        if result is None:
            raise KeyError(
                f"Decision not found: {case_id}"
            )

        return result

    def get_batch_decisions(
        self,
        batch_id: str,
    ) -> list[DecisionServiceResult]:
        case_ids = self.batches.get(
            batch_id
        )

        if not case_ids:
            raise KeyError(
                f"Batch not found: {batch_id}"
            )

        return [
            self.results[case_id]
            for case_id in case_ids
            if case_id in self.results
        ]

    def clear(self) -> None:
        self.verifications.clear()
        self.investigations.clear()
        self.results.clear()
        self.batches.clear()


store = DecisionCaseStore()


# ============================================================
# REQUEST MODELS
# ============================================================


class DecisionRequest(BaseModel):
    """
    Optional Phase 6 investigation supplied alongside
    the verification result.

    batch_id optionally associates the resulting decision
    with a batch.
    """

    investigation: InvestigationResult | None = None
    batch_id: str | None = None


class ReviewRequest(BaseModel):
    action: ReviewAction
    comment: str = Field(
        min_length=1
    )
    reviewer_id: str | None = None


# ============================================================
# SERIALIZATION
# ============================================================


def _serialize_decimal(
    value: Any,
) -> str | None:
    if value is None:
        return None

    return str(value)


def _serialize_decision(
    result: DecisionServiceResult,
) -> dict[str, Any]:
    decision = result.decision

    return {
        "case_id": decision.case_id,
        "decision": decision.decision.value,
        "reason_code": decision.reason_code.value,
        "basis": list(decision.basis),
        "financial_impact": _serialize_decimal(
            decision.financial_impact
        ),
        "materiality": decision.materiality.value,
        "policy_rule_id": decision.policy_rule_id,
        "evidence_sufficient": (
            decision.evidence_sufficient
        ),
        "investigation_validated": (
            decision.investigation_validated
        ),
        "contradictory_evidence": (
            decision.contradictory_evidence
        ),
        "supporting_evidence_ids": list(
            decision.supporting_evidence_ids
        ),
        "decision_timestamp": (
            decision.decision_timestamp.isoformat()
        ),
        "workflow_state": (
            result.workflow.state.value
        ),
        "action": {
            "action_type": result.action.action_type,
            "description": result.action.description,
        },
        "audit_entry_id": result.audit_entry_id,
    }


def _serialize_workflow(
    case_id: str,
) -> dict[str, Any]:
    workflow = service.get_workflow(
        case_id
    )

    if workflow is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Decision workflow not found: "
                f"{case_id}"
            ),
        )

    return {
        "case_id": workflow.case_id,
        "state": workflow.state.value,
        "decision": (
            workflow.decision.value
            if workflow.decision is not None
            else None
        ),
        "review_records": [
            {
                "action": record.action.value,
                "comment": record.comment,
                "reviewer_id": record.reviewer_id,
                "timestamp": record.timestamp.isoformat(),
                "previous_decision": (
                    record.previous_decision.value
                ),
                "previous_reason_code": (
                    record.previous_reason_code.value
                ),
                "human_override": record.human_override,
            }
            for record in workflow.review_records
        ],
    }


# ============================================================
# DECISION ENDPOINTS
# ============================================================


@router.post(
    "/cases/{case_id}/decision"
)
def decide_case(
    case_id: str,
    request: DecisionRequest | None = None,
) -> dict[str, Any]:
    """
    Evaluate one case using Phase 5 verification and
    optional Phase 6 investigation.

    If batch_id is supplied, the resulting decision is
    explicitly associated with that batch.
    """

    try:
        verification = store.get_verification(
            case_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    investigation = (
        request.investigation
        if request is not None
        else store.get_investigation(case_id)
    )

    batch_id = (
        request.batch_id
        if request is not None
        else None
    )

    if investigation is not None:
        store.register_investigation(
            investigation
        )

    try:
        result = service.decide(
            verification,
            investigation,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    store.save_result(
        case_id,
        result,
        batch_id=batch_id,
    )

    return _serialize_decision(
        result
    )


@router.get(
    "/cases/{case_id}/decision"
)
def get_decision(
    case_id: str,
) -> dict[str, Any]:
    """
    Return the latest Phase 7 decision for a case.
    """

    try:
        result = store.get_result(
            case_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return _serialize_decision(
        result
    )


# ============================================================
# HUMAN REVIEW
# ============================================================


@router.post(
    "/cases/{case_id}/review"
)
def review_case(
    case_id: str,
    request: ReviewRequest,
) -> dict[str, Any]:
    """
    Apply one bounded human review action.
    """

    try:
        record = service.review(
            case_id,
            request.action,
            request.comment,
            reviewer_id=request.reviewer_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return {
        "case_id": case_id,
        "action": record.action.value,
        "comment": record.comment,
        "reviewer_id": record.reviewer_id,
        "timestamp": record.timestamp.isoformat(),
        "previous_decision": (
            record.previous_decision.value
        ),
        "previous_reason_code": (
            record.previous_reason_code.value
        ),
        "human_override": record.human_override,
        "workflow_state": (
            service.get_state(case_id).value
        ),
    }


# ============================================================
# WORKFLOW
# ============================================================


@router.get(
    "/cases/{case_id}/workflow"
)
def get_case_workflow(
    case_id: str,
) -> dict[str, Any]:
    """
    Return the current case workflow state.
    """

    return _serialize_workflow(
        case_id
    )


# ============================================================
# AUDIT
# ============================================================


@router.get(
    "/cases/{case_id}/audit"
)
def get_case_audit(
    case_id: str,
) -> dict[str, Any]:
    """
    Return the append-only decision audit history.
    """

    history = service.get_audit_history(
        case_id
    )

    if not history:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Audit history not found: "
                f"{case_id}"
            ),
        )

    return {
        "case_id": case_id,
        "count": len(history),
        "entries": [
            {
                "audit_id": entry.audit_id,
                "case_id": entry.case_id,
                "verification_status": (
                    entry.verification_status
                ),
                "investigation_status": (
                    entry.investigation_status
                ),
                "evidence_ids": list(
                    entry.evidence_ids
                ),
                "policy_rule_id": (
                    entry.policy_rule_id
                ),
                "decision": (
                    entry.decision.value
                ),
                "reason_code": (
                    entry.reason_code.value
                ),
                "basis": list(entry.basis),
                "financial_impact": (
                    _serialize_decimal(
                        entry.financial_impact
                    )
                ),
                "materiality": (
                    entry.materiality.value
                ),
                "human_action": (
                    entry.human_action.value
                    if entry.human_action is not None
                    else None
                ),
                "human_comment": (
                    entry.human_comment
                ),
                "timestamp": (
                    entry.timestamp.isoformat()
                ),
            }
            for entry in history
        ],
    }


# ============================================================
# REVIEW PACKAGE
# ============================================================


@router.get(
    "/cases/{case_id}/review-package"
)
def get_review_package(
    case_id: str,
) -> dict[str, Any]:
    """
    Return the bounded human-review package.
    """

    try:
        result = store.get_result(
            case_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if result.decision.decision not in {
        DecisionOutcome.HUMAN_REVIEW,
        DecisionOutcome.RESOLVED_WITH_APPROVAL,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "Case does not currently require "
                "human review."
            ),
        )

    investigation = (
        store.get_investigation(case_id)
    )

    discrepancy_id = None
    control_id = None

    if investigation is not None:
        discrepancy_id = (
            investigation.discrepancy_id
        )

    package = service.get_review_package(
        case_id,
        discrepancy_id=discrepancy_id,
        control_id=control_id,
        investigation_status=(
            investigation.status.value
            if investigation is not None
            else None
        ),
        investigation_conclusion=(
            investigation.conclusion
            if investigation is not None
            else None
        ),
        evidence_ids=(
            investigation.supporting_evidence_ids
            if investigation is not None
            else result.decision.supporting_evidence_ids
        ),
    )

    return {
        "case_id": package.case_id,
        "financial_impact": (
            _serialize_decimal(
                package.financial_impact
            )
        ),
        "discrepancy_id": package.discrepancy_id,
        "control_id": package.control_id,
        "investigation_status": (
            package.investigation_status
        ),
        "investigation_summary": (
            package.investigation_summary
        ),
        "investigation_conclusion": (
            package.investigation_conclusion
        ),
        "evidence_ids": list(
            package.evidence_ids
        ),
        "reason_for_review": (
            package.reason_for_review
        ),
        "recommended_action": (
            package.recommended_action.value
        ),
    }


# ============================================================
# REINVESTIGATION
# ============================================================


@router.post(
    "/cases/{case_id}/reinvestigate"
)
def request_reinvestigation(
    case_id: str,
) -> dict[str, Any]:
    """
    Move a rejected or evidence-requested case into
    the explicit reinvestigation state.
    """

    try:
        state = service.request_reinvestigation(
            case_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return {
        "case_id": case_id,
        "state": state.value,
    }


@router.post(
    "/cases/{case_id}/reinvestigate/start"
)
def start_reinvestigation(
    case_id: str,
) -> dict[str, Any]:
    """
    Move REINVESTIGATION into INVESTIGATION.
    """

    try:
        state = service.start_reinvestigation(
            case_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return {
        "case_id": case_id,
        "state": state.value,
    }


# ============================================================
# BATCH CONTROL
# ============================================================


@router.get(
    "/batches/{batch_id}/control"
)
def get_batch_control(
    batch_id: str,
) -> dict[str, Any]:
    """
    Return aggregate Phase 7 control status for a batch.

    Only decisions explicitly registered to this batch are
    included in the aggregation.
    """

    try:
        results = store.get_batch_decisions(
            batch_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    decisions = [
        result.decision
        for result in results
    ]

    try:
        batch_result = batch_controller.evaluate(
            batch_id,
            decisions,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "batch_id": batch_result.batch_id,
        "total_cases": batch_result.total_cases,
        "auto_resolved": (
            batch_result.auto_resolved
        ),
        "pending": batch_result.pending,
        "human_review": (
            batch_result.human_review
        ),
        "blocked": batch_result.blocked,
        "unresolved_financial_value": (
            _serialize_decimal(
                batch_result.unresolved_financial_value
            )
        ),
        "final_control_status": (
            batch_result.final_control_status.value
        ),
    }