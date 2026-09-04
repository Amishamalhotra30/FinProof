from dataclasses import dataclass
from enum import Enum


class CorruptionType(str, Enum):
    MISSING_RECORD = "MISSING_RECORD"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    TIMING_ANOMALY = "TIMING_ANOMALY"


@dataclass(frozen=True)
class CorruptionEvent:
    case_id: str
    corruption_type: CorruptionType
    record_type: str
    record_id: str
    description: str