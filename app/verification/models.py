from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field


class ControlStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    PENDING = "PENDING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PENDING = "PENDING"
    FAILED = "FAILED"
    INDETERMINATE = "INDETERMINATE"


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Materiality(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class InvestigationStatus(str, Enum):
    UNINVESTIGATED = "UNINVESTIGATED"


class ExpectedFinancialState(BaseModel):
    """
    Financial state calculated independently from observed
    settlement and bank outcomes.

    This model represents what should have happened according
    to the financial rules applied by Phase 5.
    """

    gross_captured: Decimal = Decimal("0")

    total_refunded: Decimal = Decimal("0")

    total_fees: Decimal = Decimal("0")

    total_tax: Decimal = Decimal("0")

    total_adjustments: Decimal = Decimal("0")

    expected_settlement: Decimal = Decimal("0")

    expected_bank_credit: Decimal | None = None

    expected_event_states: dict[str, str] = Field(
        default_factory=dict
    )


class ControlCheck(BaseModel):
    """
    Result of one deterministic financial control.

    A control check describes whether an invariant holds.
    It does not explain the root cause of a failure.
    """

    control_id: str

    control_name: str

    status: ControlStatus

    expected_value: Decimal | None = None

    observed_value: Decimal | None = None

    difference: Decimal | None = None

    affected_event_ids: list[str] = Field(
        default_factory=list
    )

    supporting_evidence_ids: list[str] = Field(
        default_factory=list
    )

    severity: Severity = Severity.INFO

    blocking: bool = False


class Discrepancy(BaseModel):
    """
    A machine-readable difference between expected and
    observed financial state.

    This is intentionally not a root-cause diagnosis.
    """

    discrepancy_id: str

    control_id: str

    expected_value: Decimal | None = None

    observed_value: Decimal | None = None

    difference: Decimal = Decimal("0")

    relative_difference: Decimal | None = None

    affected_event_ids: list[str] = Field(
        default_factory=list
    )

    evidence_references: list[str] = Field(
        default_factory=list
    )

    materiality: Materiality = Materiality.NONE

    blocking: bool = False

    investigation_status: InvestigationStatus = (
        InvestigationStatus.UNINVESTIGATED
    )


class VerificationResult(BaseModel):
    """
    Complete Phase 5 verification result for one case.
    """

    case_id: str

    status: VerificationStatus

    observed_state: dict[str, Decimal] = Field(
        default_factory=dict
    )

    expected_state: ExpectedFinancialState

    controls: list[ControlCheck] = Field(
        default_factory=list
    )

    discrepancies: list[Discrepancy] = Field(
        default_factory=list
    )

    processing_time_ms: Decimal | None = None