from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


# ============================================================
# EXISTING RECONCILIATION CONTRACT
# ============================================================

class MatchStatus(str, Enum):
    MATCH = "MATCH"
    EXCEPTION = "EXCEPTION"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class ReconciliationResult:
    case_id: str
    status: MatchStatus
    confidence: Decimal
    reason: str


# ============================================================
# PHASE 3 — RELATIONSHIP CONTRACT
# ============================================================

class RelationshipType(str, Enum):
    ORDER_FOR_PAYMENT = "ORDER_FOR_PAYMENT"
    PAYMENT_FOR_ORDER = "PAYMENT_FOR_ORDER"
    REFUND_FOR_PAYMENT = "REFUND_FOR_PAYMENT"
    FEE_FOR_PAYMENT = "FEE_FOR_PAYMENT"
    ADJUSTMENT_FOR_PAYMENT = "ADJUSTMENT_FOR_PAYMENT"
    SETTLEMENT_FOR_PAYMENT = "SETTLEMENT_FOR_PAYMENT"
    BANK_FOR_SETTLEMENT = "BANK_FOR_SETTLEMENT"
    BANK_FOR_SETTLEMENT_GROUP = "BANK_FOR_SETTLEMENT_GROUP"


class Cardinality(str, Enum):
    ONE_TO_ONE = "ONE_TO_ONE"
    ONE_TO_MANY = "ONE_TO_MANY"
    MANY_TO_ONE = "MANY_TO_ONE"
    MANY_TO_MANY = "MANY_TO_MANY"


class MatchMethod(str, Enum):
    EXACT_ID = "EXACT_ID"
    NORMALIZED_ID = "NORMALIZED_ID"
    UTR_MATCH = "UTR_MATCH"
    AMOUNT_TIME_MATCH = "AMOUNT_TIME_MATCH"
    REFERENCE_SIMILARITY = "REFERENCE_SIMILARITY"
    ENTITY_SIMILARITY = "ENTITY_SIMILARITY"
    AI_ASSISTED = "AI_ASSISTED"


class RelationshipStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANDIDATE = "CANDIDATE"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class Relationship:
    relationship_id: str

    source_record_id: str
    target_record_id: str

    relationship_type: RelationshipType
    cardinality: Cardinality

    method: MatchMethod

    evidence: list[str]

    status: RelationshipStatus

    created_at: datetime