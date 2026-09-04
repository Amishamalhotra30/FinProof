from decimal import Decimal

from app.decisions.models import (
    DecisionFacts,
    DecisionOutcome,
    DecisionPolicy,
    DecisionReasonCode,
    MaterialityLevel,
)
from app.decisions.policy import (
    DecisionPolicyEngine,
)


def make_facts(**overrides) -> DecisionFacts:
    """
    Build a safe default set of decision facts.

    Individual tests override only the facts relevant to
    the decision being exercised.
    """

    values = {
        "case_id": "CASE_TEST",
        "verification_status": "FAILED",
        "investigation_status": None,
        "evidence_sufficient": False,
        "investigation_validated": False,
        "contradictory_evidence": False,
        "human_approval_required": False,
        "financial_impact": Decimal("0"),
        "materiality": MaterialityLevel.NONE,
        "explained_amount": Decimal("0"),
        "remaining_unexplained": Decimal("0"),
        "discrepancy_present": True,
        "expected_event_pending": False,
        "blocking_failure": False,
        "applicable_controls_passed": False,
    }

    values.update(overrides)

    return DecisionFacts(**values)


# ============================================================
# VERIFIED
# ============================================================


def test_verified_case_is_auto_resolved():
    facts = make_facts(
        verification_status="VERIFIED",
        discrepancy_present=False,
        applicable_controls_passed=True,
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.AUTO_RESOLVED
    )

    assert result.reason_code == (
        DecisionReasonCode.ALL_CONTROLS_PASSED
    )

    assert result.policy_rule_id == "P7-R1"


def test_verified_case_can_be_forced_to_human_review_by_policy():
    policy = DecisionPolicy(
        allow_verified_auto_resolution=False
    )

    facts = make_facts(
        verification_status="VERIFIED",
        discrepancy_present=False,
        applicable_controls_passed=True,
    )

    result = DecisionPolicyEngine(
        policy
    ).evaluate(facts)

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )


# ============================================================
# PENDING
# ============================================================


def test_expected_event_pending_returns_pending():
    facts = make_facts(
        expected_event_pending=True,
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.PENDING
    )

    assert result.reason_code == (
        DecisionReasonCode.EXPECTED_EVENT_PENDING
    )


def test_pending_takes_precedence_over_unresolved():
    facts = make_facts(
        expected_event_pending=True,
        investigation_status="UNRESOLVED",
        blocking_failure=True,
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.PENDING
    )


# ============================================================
# FULLY RESOLVED
# ============================================================


def test_fully_explained_non_material_case_auto_resolves():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=True,
        financial_impact=Decimal("50"),
        materiality=MaterialityLevel.LOW,
        explained_amount=Decimal("50"),
        remaining_unexplained=Decimal("0"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.AUTO_RESOLVED
    )

    assert result.reason_code == (
        DecisionReasonCode.FULLY_EXPLAINED_NON_MATERIAL
    )

    assert result.policy_rule_id == "P7-R4"


def test_fully_explained_high_materiality_requires_approval():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=True,
        financial_impact=Decimal("5000"),
        materiality=MaterialityLevel.HIGH,
        explained_amount=Decimal("5000"),
        remaining_unexplained=Decimal("0"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )

    assert result.reason_code == (
        DecisionReasonCode.FULLY_EXPLAINED_REQUIRES_APPROVAL
    )


def test_fully_explained_case_above_auto_threshold_requires_approval():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=True,
        financial_impact=Decimal("2000"),
        materiality=MaterialityLevel.MEDIUM,
        explained_amount=Decimal("2000"),
        remaining_unexplained=Decimal("0"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )


def test_explicit_human_approval_requirement_is_respected():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=True,
        human_approval_required=True,
        financial_impact=Decimal("50"),
        materiality=MaterialityLevel.LOW,
        explained_amount=Decimal("50"),
        remaining_unexplained=Decimal("0"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )


# ============================================================
# INVESTIGATION SAFETY
# ============================================================


def test_insufficient_evidence_requires_human_review():
    facts = make_facts(
        investigation_status="INSUFFICIENT_EVIDENCE",
        evidence_sufficient=False,
        investigation_validated=False,
        financial_impact=Decimal("500"),
        materiality=MaterialityLevel.MEDIUM,
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )

    assert result.reason_code == (
        DecisionReasonCode.INSUFFICIENT_EVIDENCE
    )


def test_contradictory_evidence_requires_human_review():
    facts = make_facts(
        investigation_status="CONTRADICTION",
        contradictory_evidence=True,
        financial_impact=Decimal("500"),
        materiality=MaterialityLevel.MEDIUM,
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )

    assert result.reason_code == (
        DecisionReasonCode.CONTRADICTORY_EVIDENCE
    )


def test_contradiction_takes_precedence_over_resolved():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=True,
        contradictory_evidence=True,
        financial_impact=Decimal("50"),
        materiality=MaterialityLevel.LOW,
        explained_amount=Decimal("50"),
        remaining_unexplained=Decimal("0"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )


def test_resolved_but_not_validated_cannot_auto_resolve():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=False,
        financial_impact=Decimal("50"),
        materiality=MaterialityLevel.LOW,
        explained_amount=Decimal("50"),
        remaining_unexplained=Decimal("0"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )


def test_resolved_with_remaining_unexplained_cannot_auto_resolve():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=True,
        financial_impact=Decimal("100"),
        materiality=MaterialityLevel.LOW,
        explained_amount=Decimal("75"),
        remaining_unexplained=Decimal("25"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )


# ============================================================
# BLOCKING
# ============================================================


def test_material_blocking_unresolved_case_is_blocked():
    facts = make_facts(
        investigation_status="UNRESOLVED",
        financial_impact=Decimal("5000"),
        materiality=MaterialityLevel.HIGH,
        blocking_failure=True,
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.BLOCKED
    )

    assert result.reason_code == (
        DecisionReasonCode.MATERIAL_UNRESOLVED
    )


def test_non_blocking_unresolved_case_requires_human_review():
    facts = make_facts(
        investigation_status="UNRESOLVED",
        financial_impact=Decimal("5000"),
        materiality=MaterialityLevel.HIGH,
        blocking_failure=False,
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.decision == (
        DecisionOutcome.HUMAN_REVIEW
    )


# ============================================================
# POLICY CONFIGURATION
# ============================================================


def test_invalid_policy_thresholds_are_rejected():
    policy = DecisionPolicy(
        auto_resolution_threshold=Decimal(
            "5000"
        ),
        human_approval_threshold=Decimal(
            "1000"
        ),
    )

    try:
        DecisionPolicyEngine(policy)
    except ValueError:
        return

    raise AssertionError(
        "Invalid policy thresholds should raise ValueError"
    )


# ============================================================
# AUDITABLE RESULT
# ============================================================


def test_decision_contains_machine_readable_basis():
    facts = make_facts(
        investigation_status="RESOLVED",
        evidence_sufficient=True,
        investigation_validated=True,
        financial_impact=Decimal("50"),
        materiality=MaterialityLevel.LOW,
        explained_amount=Decimal("50"),
        remaining_unexplained=Decimal("0"),
    )

    result = DecisionPolicyEngine().evaluate(
        facts
    )

    assert result.case_id == "CASE_TEST"
    assert result.policy_rule_id
    assert result.reason_code
    assert result.basis
    assert result.financial_impact == Decimal(
        "50"
    )