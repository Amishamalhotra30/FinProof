from dataclasses import dataclass
from enum import Enum

from app.verification.models import Severity


class RuleInput(str, Enum):
    OBSERVED_STATE = "OBSERVED_STATE"
    EXPECTED_STATE = "EXPECTED_STATE"
    EVENT_GRAPH = "EVENT_GRAPH"
    EVENT_CHAINS = "EVENT_CHAINS"
    EVIDENCE = "EVIDENCE"


@dataclass(frozen=True)
class RuleDefinition:
    rule_id: str
    name: str
    description: str
    inputs: tuple[RuleInput, ...]
    expected_condition: str
    severity: Severity
    blocking: bool


RULE_AMOUNT_CONSERVATION = RuleDefinition(
    rule_id="AMOUNT_CONSERVATION",
    name="Amount conservation",
    description=(
        "Observed financial amounts must satisfy "
        "the independently calculated expected state."
    ),
    inputs=(
        RuleInput.EXPECTED_STATE,
        RuleInput.OBSERVED_STATE,
    ),
    expected_condition=(
        "Expected and observed financial amounts agree."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


RULE_SETTLEMENT_COMPOSITION = RuleDefinition(
    rule_id="SETTLEMENT_COMPOSITION",
    name="Settlement composition",
    description=(
        "Expected settlement must equal captured amount "
        "minus refunds and fees plus adjustments."
    ),
    inputs=(
        RuleInput.EXPECTED_STATE,
        RuleInput.OBSERVED_STATE,
    ),
    expected_condition=(
        "gross - refunds - fees + adjustments "
        "equals expected settlement."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


RULE_REFUND_BOUNDS = RuleDefinition(
    rule_id="REFUND_BOUNDS",
    name="Refund bounds",
    description=(
        "Total refunds must not exceed the captured amount."
    ),
    inputs=(
        RuleInput.OBSERVED_STATE,
        RuleInput.EVENT_GRAPH,
    ),
    expected_condition=(
        "total refunds are less than or equal to "
        "gross captured amount."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


RULE_FEE_ADJUSTMENT_ACCOUNTING = RuleDefinition(
    rule_id="FEE_ADJUSTMENT_ACCOUNTING",
    name="Fee and adjustment accounting",
    description=(
        "Fees and adjustments must be represented "
        "according to their defined financial semantics."
    ),
    inputs=(
        RuleInput.EXPECTED_STATE,
        RuleInput.OBSERVED_STATE,
    ),
    expected_condition=(
        "Observed fees and adjustments agree with "
        "the expected financial state."
    ),
    severity=Severity.MEDIUM,
    blocking=True,
)


RULE_EVENT_ORDERING = RuleDefinition(
    rule_id="EVENT_ORDERING",
    name="Event ordering",
    description=(
        "Financial lifecycle events must occur in "
        "a valid temporal order."
    ),
    inputs=(
        RuleInput.EVENT_GRAPH,
        RuleInput.EVENT_CHAINS,
    ),
    expected_condition=(
        "Lifecycle predecessor events occur before "
        "their dependent events."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


RULE_SETTLEMENT_TIMING = RuleDefinition(
    rule_id="SETTLEMENT_TIMING",
    name="Settlement timing",
    description=(
        "Settlement and downstream bank events must "
        "respect the configured lifecycle timing window."
    ),
    inputs=(
        RuleInput.EVENT_GRAPH,
        RuleInput.EVENT_CHAINS,
    ),
    expected_condition=(
        "Observed downstream events occur within "
        "the permitted settlement window."
    ),
    severity=Severity.MEDIUM,
    blocking=False,
)


RULE_DUPLICATE_PROTECTION = RuleDefinition(
    rule_id="DUPLICATE_PROTECTION",
    name="Duplicate protection",
    description=(
        "The same financial event must not contribute "
        "financial impact more than once."
    ),
    inputs=(
        RuleInput.EVENT_GRAPH,
        RuleInput.EVENT_CHAINS,
    ),
    expected_condition=(
        "Equivalent observations are not double counted."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


RULE_CURRENCY_CONSISTENCY = RuleDefinition(
    rule_id="CURRENCY_CONSISTENCY",
    name="Currency consistency",
    description=(
        "Amounts participating in the same financial "
        "calculation must use a consistent currency."
    ),
    inputs=(
        RuleInput.EVENT_GRAPH,
        RuleInput.EVENT_CHAINS,
    ),
    expected_condition=(
        "Related financial events use compatible currencies."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


RULE_SETTLEMENT_BANK_RELATIONSHIP = RuleDefinition(
    rule_id="SETTLEMENT_BANK_RELATIONSHIP",
    name="Settlement to bank relationship",
    description=(
        "Bank credit must be consistent with the "
        "modeled settlement lifecycle."
    ),
    inputs=(
        RuleInput.EVENT_GRAPH,
        RuleInput.EVENT_CHAINS,
        RuleInput.OBSERVED_STATE,
    ),
    expected_condition=(
        "Bank credit is consistent with settlement "
        "amount and lifecycle timing."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


RULE_EXPECTED_EVENT_EXISTENCE = RuleDefinition(
    rule_id="EXPECTED_EVENT_EXISTENCE",
    name="Expected event existence",
    description=(
        "Required downstream observations must exist "
        "when their lifecycle window has expired."
    ),
    inputs=(
        RuleInput.EVENT_GRAPH,
        RuleInput.EVENT_CHAINS,
    ),
    expected_condition=(
        "Required lifecycle events are observed or "
        "remain within their allowed pending window."
    ),
    severity=Severity.HIGH,
    blocking=True,
)


PHASE5_RULES: tuple[RuleDefinition, ...] = (
    RULE_AMOUNT_CONSERVATION,
    RULE_SETTLEMENT_COMPOSITION,
    RULE_REFUND_BOUNDS,
    RULE_FEE_ADJUSTMENT_ACCOUNTING,
    RULE_EVENT_ORDERING,
    RULE_SETTLEMENT_TIMING,
    RULE_DUPLICATE_PROTECTION,
    RULE_CURRENCY_CONSISTENCY,
    RULE_SETTLEMENT_BANK_RELATIONSHIP,
    RULE_EXPECTED_EVENT_EXISTENCE,
)


def get_rule(rule_id: str) -> RuleDefinition:
    for rule in PHASE5_RULES:
        if rule.rule_id == rule_id:
            return rule

    raise KeyError(f"Unknown Phase 5 rule: {rule_id}")