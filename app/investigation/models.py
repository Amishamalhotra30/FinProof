from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


# ============================================================
# Investigation Status
# ============================================================


class InvestigationStatus(str, Enum):
    """
    Overall state of a Phase 6 investigation.
    """

    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTION = "CONTRADICTION"


# ============================================================
# Hypothesis Types
# ============================================================


class HypothesisType(str, Enum):
    """
    Controlled vocabulary of financial explanations that the
    Phase 6 investigator is allowed to consider.

    The vocabulary is intentionally bounded so that the agent
    cannot invent arbitrary financial root-cause categories.
    """

    REFUND = "REFUND"
    FEE = "FEE"
    TAX = "TAX"
    ADJUSTMENT = "ADJUSTMENT"
    PARTIAL_SETTLEMENT = "PARTIAL_SETTLEMENT"
    BUNDLED_SETTLEMENT = "BUNDLED_SETTLEMENT"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    TIMING_DIFFERENCE = "TIMING_DIFFERENCE"
    MISSING_EVENT = "MISSING_EVENT"
    SOURCE_DATA_ERROR = "SOURCE_DATA_ERROR"
    UNDETERMINED = "UNDETERMINED"


# ============================================================
# Hypothesis Status
# ============================================================


class HypothesisStatus(str, Enum):
    """
    Deterministic reasoning state assigned to a hypothesis.

    These are intentionally not confidence scores.
    """

    SUPPORTED = "SUPPORTED"
    WEAKLY_SUPPORTED = "WEAKLY_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNDETERMINED = "UNDETERMINED"


# ============================================================
# Evidence Relation
# ============================================================


class EvidenceRelation(str, Enum):
    """
    Relationship between a retrieved evidence item and a
    hypothesis.
    """

    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    IRRELEVANT = "IRRELEVANT"
    MISSING = "MISSING"


# ============================================================
# Investigation Evidence
# ============================================================


class InvestigationEvidence(BaseModel):
    """
    A piece of evidence retrieved during investigation.

    Evidence is descriptive and provenance-preserving.
    It does not represent an AI-generated financial fact.
    """

    evidence_id: str
    source: str
    record_id: str

    amount: Decimal | None = None

    timestamp: str | None = None

    relationship: EvidenceRelation = (
        EvidenceRelation.IRRELEVANT
    )

    description: str | None = None

    metadata: dict[str, str] = Field(
        default_factory=dict
    )


# ============================================================
# Investigation Hypothesis
# ============================================================


class InvestigationHypothesis(BaseModel):
    """
    One candidate explanation for a Phase 5 discrepancy.
    """

    hypothesis_id: str

    hypothesis_type: HypothesisType

    status: HypothesisStatus = (
        HypothesisStatus.UNDETERMINED
    )

    description: str | None = None

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    explained_amount: Decimal = Decimal("0")

    contradicting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    required_evidence: list[str] = Field(
        default_factory=list
    )


# ============================================================
# Investigation Case
# ============================================================


class InvestigationCase(BaseModel):
    """
    Structured input to the Phase 6 investigation engine.

    This is created from a Phase 5 discrepancy and contains
    only the information required to investigate that
    discrepancy.
    """

    case_id: str

    discrepancy_id: str

    control_failure: str

    affected_event_ids: list[str] = Field(
        default_factory=list
    )

    expected_value: Decimal | None = None

    observed_value: Decimal | None = None

    difference: Decimal

    expected_state: dict[str, Decimal] = Field(
        default_factory=dict
    )

    observed_state: dict[str, Decimal] = Field(
        default_factory=dict
    )


# ============================================================
# Hypothesis Finding
# ============================================================


class HypothesisFinding(BaseModel):
    """
    Structured result of evaluating one hypothesis.
    """

    hypothesis_type: HypothesisType

    status: HypothesisStatus

    explained_amount: Decimal = Decimal("0")

    evidence_ids: list[str] = Field(
        default_factory=list
    )

    contradicting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    reasoning: str | None = None


# ============================================================
# Investigation Result
# ============================================================


class InvestigationResult(BaseModel):
    """
    Complete structured output of Phase 6.

    Numerical explanation is represented explicitly so that
    application code can independently validate it.
    """

    investigation_id: str

    case_id: str

    discrepancy_id: str

    status: InvestigationStatus

    hypotheses: list[HypothesisFinding] = Field(
        default_factory=list
    )

    explained_amount: Decimal = Decimal("0")

    remaining_unexplained: Decimal = Decimal("0")

    supporting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    conclusion: str | None = None

    validated: bool = False