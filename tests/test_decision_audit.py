from decimal import Decimal

from app.decisions.audit import AuditLog
from app.decisions.actions import (
    DecisionActionExecutor,
)
from app.decisions.models import (
    DecisionOutcome,
    DecisionReasonCode,
    DecisionResult,
    MaterialityLevel,
    ReviewAction,
)


def make_decision(
    decision=DecisionOutcome.HUMAN_REVIEW,
    reason_code=DecisionReasonCode.INSUFFICIENT_EVIDENCE,
):
    return DecisionResult(
        case_id="CASE_AUDIT_TEST",
        decision=decision,
        reason_code=reason_code,
        basis=[
            "Evidence is insufficient."
        ],
        financial_impact=Decimal("500"),
        materiality=MaterialityLevel.MEDIUM,
        policy_rule_id="P7-R10",
        evidence_sufficient=False,
        investigation_validated=False,
        contradictory_evidence=False,
        supporting_evidence_ids=[
            "EV-001",
            "EV-002",
        ],
    )


def test_audit_log_starts_empty():
    audit = AuditLog()

    assert audit.entries == ()
    assert audit.count() == 0


def test_decision_is_recorded():
    audit = AuditLog()

    decision = make_decision()

    entry = audit.record_decision(
        decision,
        verification_status="FAILED",
        investigation_status="INSUFFICIENT_EVIDENCE",
    )

    assert entry.case_id == "CASE_AUDIT_TEST"
    assert entry.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )
    assert entry.reason_code == (
        DecisionReasonCode.INSUFFICIENT_EVIDENCE
    )


def test_decision_audit_preserves_evidence_ids():
    audit = AuditLog()

    decision = make_decision()

    entry = audit.record_decision(
        decision,
        verification_status="FAILED",
    )

    assert entry.evidence_ids == [
        "EV-001",
        "EV-002",
    ]


def test_decision_audit_preserves_policy_rule():
    audit = AuditLog()

    decision = make_decision()

    entry = audit.record_decision(
        decision,
        verification_status="FAILED",
    )

    assert entry.policy_rule_id == "P7-R10"


def test_decision_audit_preserves_financial_impact():
    audit = AuditLog()

    decision = make_decision()

    entry = audit.record_decision(
        decision,
        verification_status="FAILED",
    )

    assert entry.financial_impact == Decimal(
        "500"
    )


def test_case_history_returns_only_requested_case():
    audit = AuditLog()

    first = make_decision()

    second = DecisionResult(
        case_id="CASE_OTHER",
        decision=DecisionOutcome.BLOCKED,
        reason_code=DecisionReasonCode.MATERIAL_UNRESOLVED,
        basis=["Blocking failure."],
        financial_impact=Decimal("5000"),
        materiality=MaterialityLevel.HIGH,
        policy_rule_id="P7-R9",
    )

    audit.record_decision(
        first,
        verification_status="FAILED",
    )

    audit.record_decision(
        second,
        verification_status="FAILED",
    )

    history = audit.get_case_history(
        "CASE_AUDIT_TEST"
    )

    assert len(history) == 1
    assert history[0].case_id == (
        "CASE_AUDIT_TEST"
    )


def test_audit_entries_are_append_only():
    audit = AuditLog()

    decision = make_decision()

    first = audit.record_decision(
        decision,
        verification_status="FAILED",
    )

    second = audit.record_decision(
        decision,
        verification_status="FAILED",
    )

    assert audit.count() == 2
    assert first.audit_id != second.audit_id


def test_human_review_is_appended_as_new_entry():
    audit = AuditLog()

    decision = make_decision()

    decision_entry = audit.record_decision(
        decision,
        verification_status="FAILED",
        investigation_status="INSUFFICIENT_EVIDENCE",
    )

    review = (
        DecisionActionExecutor()
        .record_review(
            decision,
            ReviewAction.REQUEST_MORE_EVIDENCE,
            "Need additional bank evidence.",
            reviewer_id="REVIEWER-001",
        )
    )

    review_entry = audit.record_human_review(
        review,
        verification_status="FAILED",
        investigation_status="INSUFFICIENT_EVIDENCE",
        evidence_ids=["EV-001"],
    )

    history = audit.get_case_history(
        "CASE_AUDIT_TEST"
    )

    assert len(history) == 2
    assert history[0].audit_id == (
        decision_entry.audit_id
    )
    assert history[1].audit_id == (
        review_entry.audit_id
    )


def test_request_more_evidence_has_correct_reason():
    audit = AuditLog()

    decision = make_decision()

    review = (
        DecisionActionExecutor()
        .record_review(
            decision,
            ReviewAction.REQUEST_MORE_EVIDENCE,
            "Need bank statement.",
        )
    )

    entry = audit.record_human_review(
        review,
        verification_status="FAILED",
    )

    assert entry.reason_code == (
        DecisionReasonCode.MORE_EVIDENCE_REQUESTED
    )


def test_rejection_has_correct_reason():
    audit = AuditLog()

    decision = make_decision()

    review = (
        DecisionActionExecutor()
        .record_review(
            decision,
            ReviewAction.REJECT,
            "The explanation is not sufficient.",
        )
    )

    entry = audit.record_human_review(
        review,
        verification_status="FAILED",
    )

    assert entry.reason_code == (
        DecisionReasonCode.REVIEW_REJECTED
    )


def test_approval_has_correct_reason():
    audit = AuditLog()

    decision = DecisionResult(
        case_id="CASE_APPROVAL",
        decision=DecisionOutcome.RESOLVED_WITH_APPROVAL,
        reason_code=(
            DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL
        ),
        basis=[
            "Human approval required."
        ],
        financial_impact=Decimal("5000"),
        materiality=MaterialityLevel.HIGH,
        policy_rule_id="P7-R5",
        evidence_sufficient=True,
        investigation_validated=True,
    )

    review = (
        DecisionActionExecutor()
        .record_review(
            decision,
            ReviewAction.APPROVE,
            "Reviewed and approved.",
            reviewer_id="REVIEWER-001",
        )
    )

    entry = audit.record_human_review(
        review,
        verification_status="FAILED",
        investigation_status="RESOLVED",
    )

    assert entry.reason_code == (
        DecisionReasonCode.REVIEW_APPROVED
    )


def test_get_returns_entry_by_audit_id():
    audit = AuditLog()

    decision = make_decision()

    entry = audit.record_decision(
        decision,
        verification_status="FAILED",
    )

    found = audit.get(entry.audit_id)

    assert found is entry


def test_get_returns_none_for_unknown_id():
    audit = AuditLog()

    assert audit.get("AUDIT-NOT-FOUND") is None


def test_case_count_is_correct():
    audit = AuditLog()

    decision_a = make_decision()

    decision_b = DecisionResult(
        case_id="CASE_B",
        decision=DecisionOutcome.PENDING,
        reason_code=DecisionReasonCode.EXPECTED_EVENT_PENDING,
        basis=["Waiting for settlement."],
        policy_rule_id="P7-R2",
    )

    audit.record_decision(
        decision_a,
        verification_status="FAILED",
    )

    audit.record_decision(
        decision_b,
        verification_status="PENDING",
    )

    assert audit.count() == 2
    assert audit.count(
        "CASE_AUDIT_TEST"
    ) == 1
    assert audit.count("CASE_B") == 1