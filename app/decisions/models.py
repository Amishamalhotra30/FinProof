from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================
# DECISION OUTCOMES
# ============================================================


class DecisionOutcome(str, Enum):
    """
    Final bounded operational decision produced by Phase 7.

    These outcomes describe control workflow actions only.
    They do not perform financial mutations.
    """

    AUTO_RESOLVED = "AUTO_RESOLVED"
    PENDING = "PENDING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    RESOLVED_WITH_APPROVAL = "RESOLVED_WITH_APPROVAL"
    BLOCKED = "BLOCKED"


# ============================================================
# CASE WORKFLOW STATES
# ============================================================


class CaseState(str, Enum):
    """
    Explicit lifecycle states for a Phase 7 case.

    The state machine is deliberately separate from the final
    decision outcome because HUMAN_REVIEW may later lead to
    approval, rejection, or more evidence.
    """

    OPEN = "OPEN"
    VERIFICATION = "VERIFICATION"
    INVESTIGATION = "INVESTIGATION"
    DECISION = "DECISION"

    AUTO_RESOLVED = "AUTO_RESOLVED"
    PENDING = "PENDING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    BLOCKED = "BLOCKED"

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
    REINVESTIGATION = "REINVESTIGATION"


# ============================================================
# HUMAN REVIEW ACTIONS
# ============================================================


class ReviewAction(str, Enum):
    """
    Allowed human actions.

    No financial mutation is exposed through this enum.
    """

    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"


# ============================================================
# REASON CODES
# ============================================================


class DecisionReasonCode(str, Enum):
    """
    Machine-readable explanation for a Phase 7 decision.

    Reason codes are intentionally deterministic and auditable.
    """

    ALL_CONTROLS_PASSED = (
        "ALL_CONTROLS_PASSED"
    )

    EXPECTED_EVENT_PENDING = (
        "EXPECTED_EVENT_PENDING"
    )

    FULLY_EXPLAINED_NON_MATERIAL = (
        "FULLY_EXPLAINED_NON_MATERIAL"
    )

    FULLY_EXPLAINED_REQUIRES_APPROVAL = (
        "FULLY_EXPLAINED_REQUIRES_APPROVAL"
    )

    INSUFFICIENT_EVIDENCE = (
        "INSUFFICIENT_EVIDENCE"
    )

    CONTRADICTORY_EVIDENCE = (
        "CONTRADICTORY_EVIDENCE"
    )

    MATERIAL_UNRESOLVED = (
        "MATERIAL_UNRESOLVED"
    )

    POLICY_REQUIRES_HUMAN = (
        "POLICY_REQUIRES_HUMAN"
    )

    MATERIAL_CONTROL_FAILURE = (
        "MATERIAL_CONTROL_FAILURE"
    )

    UNRESOLVED_DISCREPANCY = (
        "UNRESOLVED_DISCREPANCY"
    )

    REVIEW_APPROVED = (
        "REVIEW_APPROVED"
    )

    REVIEW_REJECTED = (
        "REVIEW_REJECTED"
    )

    MORE_EVIDENCE_REQUESTED = (
        "MORE_EVIDENCE_REQUESTED"
    )


# ============================================================
# MATERIALITY POLICY
# ============================================================


class MaterialityLevel(str, Enum):
    """
    Phase 7 policy-level materiality classification.

    This mirrors the existing Phase 5 materiality vocabulary
    without modifying the Phase 5 model.
    """

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ============================================================
# MERCHANT CONTROL POLICY
# ============================================================


class DecisionPolicy(BaseModel):
    """
    Configurable synthetic merchant policy used by Phase 7.

    These are policy controls, not universal accounting rules.
    """

    auto_resolution_threshold: Decimal = Decimal(
        "1000.00"
    )

    human_approval_threshold: Decimal = Decimal(
        "100000.00"
    )

    block_material_unresolved: bool = True

    require_human_for_medium_materiality: bool = False

    require_human_for_high_materiality: bool = True

    allow_verified_auto_resolution: bool = True

    allow_non_material_auto_resolution: bool = True

    def validate_configuration(self) -> None:
        """
        Validate policy configuration.

        Thresholds must be non-negative and logically ordered.
        """

        if self.auto_resolution_threshold < Decimal(
            "0"
        ):
            raise ValueError(
                "auto_resolution_threshold must be "
                "non-negative"
            )

        if self.human_approval_threshold < Decimal(
            "0"
        ):
            raise ValueError(
                "human_approval_threshold must be "
                "non-negative"
            )

        if (
            self.human_approval_threshold
            < self.auto_resolution_threshold
        ):
            raise ValueError(
                "human_approval_threshold must be "
                "greater than or equal to "
                "auto_resolution_threshold"
            )


# ============================================================
# DECISION FACTS
# ============================================================


class DecisionFacts(BaseModel):
    """
    Structured facts supplied to the deterministic policy engine.

    The policy engine decides from these facts.

    An LLM is never required to produce the final decision.
    """

    case_id: str

    verification_status: str

    investigation_status: str | None = None

    evidence_sufficient: bool = False

    investigation_validated: bool = False

    contradictory_evidence: bool = False

    human_approval_required: bool = False

    financial_impact: Decimal = Decimal("0")

    materiality: MaterialityLevel = (
        MaterialityLevel.NONE
    )

    explained_amount: Decimal = Decimal("0")

    remaining_unexplained: Decimal = Decimal(
        "0"
    )

    discrepancy_present: bool = False

    expected_event_pending: bool = False

    blocking_failure: bool = False

    applicable_controls_passed: bool = False


# ============================================================
# DECISION RESULT
# ============================================================


class DecisionResult(BaseModel):
    """
    Final deterministic Phase 7 decision.

    This is the central output consumed by later workflow,
    audit and API layers.
    """

    case_id: str

    decision: DecisionOutcome

    reason_code: DecisionReasonCode

    basis: list[str] = Field(
        default_factory=list
    )

    financial_impact: Decimal = Decimal("0")

    materiality: MaterialityLevel = (
        MaterialityLevel.NONE
    )

    policy_rule_id: str

    evidence_sufficient: bool = False

    investigation_validated: bool = False

    contradictory_evidence: bool = False

    supporting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    decision_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


# ============================================================
# HUMAN REVIEW PACKAGE
# ============================================================


class HumanReviewPackage(BaseModel):
    """
    Bounded package presented to a human reviewer.

    The reviewer receives the relevant financial-control
    context rather than unrestricted source data.
    """

    case_id: str

    financial_impact: Decimal = Decimal("0")

    discrepancy_id: str | None = None

    control_id: str | None = None

    investigation_status: str | None = None

    investigation_summary: str | None = None

    investigation_conclusion: str | None = None

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    reason_for_review: str

    recommended_action: DecisionOutcome


# ============================================================
# HUMAN REVIEW RECORD
# ============================================================


class HumanReviewRecord(BaseModel):
    """
    Immutable record of one human review action.

    Historical review records must never be overwritten.
    """

    case_id: str

    action: ReviewAction

    comment: str

    reviewer_id: str | None = None

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    previous_decision: DecisionOutcome

    previous_reason_code: DecisionReasonCode

    human_override: bool = True


# ============================================================
# AUDIT ENTRY
# ============================================================


class DecisionAuditEntry(BaseModel):
    """
    Immutable audit representation of a Phase 7 decision.

    Every decision must retain enough information to explain
    why the controller reached the outcome.
    """

    audit_id: str

    case_id: str

    verification_status: str

    investigation_status: str | None = None

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    policy_rule_id: str

    decision: DecisionOutcome

    reason_code: DecisionReasonCode

    basis: list[str] = Field(
        default_factory=list
    )

    financial_impact: Decimal = Decimal("0")

    materiality: MaterialityLevel = (
        MaterialityLevel.NONE
    )

    human_action: ReviewAction | None = None

    human_comment: str | None = None

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )


# ============================================================
# BATCH CONTROL STATUS
# ============================================================


class BatchControlStatus(str, Enum):
    """
    Final control state for a batch/period.
    """

    READY_TO_CLOSE = "READY_TO_CLOSE"

    READY_WITH_NON_MATERIAL_EXCEPTIONS = (
        "READY_WITH_NON_MATERIAL_EXCEPTIONS"
    )

    REVIEW_REQUIRED = "REVIEW_REQUIRED"

    BLOCKED = "BLOCKED"


# ============================================================
# BATCH CONTROL RESULT
# ============================================================


class BatchControlResult(BaseModel):
    """
    Aggregate Phase 7 control result for a batch.
    """

    batch_id: str

    total_cases: int = 0

    auto_resolved: int = 0

    pending: int = 0

    human_review: int = 0

    blocked: int = 0

    unresolved_financial_value: Decimal = (
        Decimal("0")
    )

    final_control_status: BatchControlStatus = (
        BatchControlStatus.READY_TO_CLOSE
    )


# ============================================================
# CASE WORKFLOW RECORD
# ============================================================


class CaseWorkflow(BaseModel):
    """
    Current state of a case within the Phase 7 state machine.

    History is preserved separately through audit entries.
    """

    case_id: str

    state: CaseState = CaseState.OPEN

    decision: DecisionOutcome | None = None

    review_package: HumanReviewPackage | None = None

    review_records: list[HumanReviewRecord] = (
        Field(default_factory=list)
    )
