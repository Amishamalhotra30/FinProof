from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.decisions.models import (
    DecisionAuditEntry,
    DecisionResult,
    HumanReviewRecord,
)


class AuditLog:
    """
    Append-only audit log for Phase 7.

    Audit entries are immutable once created and existing
    entries are never overwritten or deleted through this API.
    """

    def __init__(self) -> None:
        self._entries: list[DecisionAuditEntry] = []

    @property
    def entries(
        self,
    ) -> tuple[DecisionAuditEntry, ...]:
        """
        Return the complete audit history as an immutable tuple.
        """

        return tuple(self._entries)

    def record_decision(
        self,
        decision: DecisionResult,
        *,
        verification_status: str,
        investigation_status: str | None = None,
    ) -> DecisionAuditEntry:
        """
        Record one deterministic Phase 7 decision.
        """

        entry = DecisionAuditEntry(
            audit_id=self._new_audit_id(),
            case_id=decision.case_id,
            verification_status=verification_status,
            investigation_status=investigation_status,
            evidence_ids=list(
                decision.supporting_evidence_ids
            ),
            policy_rule_id=decision.policy_rule_id,
            decision=decision.decision,
            reason_code=decision.reason_code,
            basis=list(decision.basis),
            financial_impact=decision.financial_impact,
            materiality=decision.materiality,
            timestamp=datetime.now(timezone.utc),
        )

        self._entries.append(entry)

        return entry

    def record_human_review(
        self,
        review: HumanReviewRecord,
        *,
        verification_status: str,
        investigation_status: str | None = None,
        evidence_ids: list[str] | None = None,
        policy_rule_id: str = "HUMAN-REVIEW",
    ) -> DecisionAuditEntry:
        """
        Record one human intervention.

        Human actions are appended as new audit entries.
        Existing decision history is preserved.
        """

        if evidence_ids is None:
            evidence_ids = []

        entry = DecisionAuditEntry(
            audit_id=self._new_audit_id(),
            case_id=review.case_id,
            verification_status=verification_status,
            investigation_status=investigation_status,
            evidence_ids=list(evidence_ids),
            policy_rule_id=policy_rule_id,
            decision=self._decision_for_review(
                review
            ),
            reason_code=self._reason_for_review(
                review
            ),
            basis=[
                "Human review action recorded.",
                review.comment,
            ],
            financial_impact=0,
            materiality="NONE",
            human_action=review.action,
            human_comment=review.comment,
            timestamp=review.timestamp,
        )

        self._entries.append(entry)

        return entry

    def get_case_history(
        self,
        case_id: str,
    ) -> tuple[DecisionAuditEntry, ...]:
        """
        Return all audit entries for one case in insertion order.
        """

        return tuple(
            entry
            for entry in self._entries
            if entry.case_id == case_id
        )

    def get(
        self,
        audit_id: str,
    ) -> DecisionAuditEntry | None:
        """
        Find an audit entry by ID.
        """

        for entry in self._entries:
            if entry.audit_id == audit_id:
                return entry

        return None

    def count(
        self,
        case_id: str | None = None,
    ) -> int:
        """
        Count audit entries globally or for one case.
        """

        if case_id is None:
            return len(self._entries)

        return sum(
            1
            for entry in self._entries
            if entry.case_id == case_id
        )

    @staticmethod
    def _new_audit_id() -> str:
        return f"AUDIT-{uuid4().hex}"

    @staticmethod
    def _decision_for_review(
        review: HumanReviewRecord,
    ):
        """
        Map the human action to the resulting workflow decision.

        This records the human action without changing financial
        records or pretending that approval itself is a financial
        mutation.
        """

        from app.decisions.models import DecisionOutcome

        if review.action.value == "APPROVE":
            return DecisionOutcome.AUTO_RESOLVED

        if review.action.value == "REJECT":
            return DecisionOutcome.HUMAN_REVIEW

        return DecisionOutcome.HUMAN_REVIEW

    @staticmethod
    def _reason_for_review(
        review: HumanReviewRecord,
    ):
        """
        Preserve a deterministic reason code for the human action.
        """

        from app.decisions.models import DecisionReasonCode

        if review.action.value == "APPROVE":
            return DecisionReasonCode.REVIEW_APPROVED

        if review.action.value == "REJECT":
            return DecisionReasonCode.REVIEW_REJECTED

        return DecisionReasonCode.MORE_EVIDENCE_REQUESTED


def record_decision(
    audit_log: AuditLog,
    decision: DecisionResult,
    *,
    verification_status: str,
    investigation_status: str | None = None,
) -> DecisionAuditEntry:
    """
    Convenience wrapper for decision auditing.
    """

    return audit_log.record_decision(
        decision,
        verification_status=verification_status,
        investigation_status=investigation_status,
    )


def record_human_review(
    audit_log: AuditLog,
    review: HumanReviewRecord,
    *,
    verification_status: str,
    investigation_status: str | None = None,
    evidence_ids: list[str] | None = None,
    policy_rule_id: str = "HUMAN-REVIEW",
) -> DecisionAuditEntry:
    """
    Convenience wrapper for human-review auditing.
    """

    return audit_log.record_human_review(
        review,
        verification_status=verification_status,
        investigation_status=investigation_status,
        evidence_ids=evidence_ids,
        policy_rule_id=policy_rule_id,
    )