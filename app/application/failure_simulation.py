from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FailureMode(str, Enum):
    """Controlled failure modes used by the Phase 9 demo."""

    NONE = "NONE"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    EVIDENCE_RETRIEVAL_FAILURE = "EVIDENCE_RETRIEVAL_FAILURE"
    MALFORMED_AI_OUTPUT = "MALFORMED_AI_OUTPUT"
    MISSING_ADJUSTMENT_SOURCE = "MISSING_ADJUSTMENT_SOURCE"
    DUPLICATE_BANK_RECORD = "DUPLICATE_BANK_RECORD"
    AMBIGUOUS_SETTLEMENT = "AMBIGUOUS_SETTLEMENT"


@dataclass(frozen=True)
class FailureSimulation:
    """
    Immutable configuration describing one controlled demo failure.

    This module intentionally does not modify reconciliation, reconstruction,
    verification, investigation, or decision logic. Integration is added
    separately in the pipeline/API layer.
    """

    mode: FailureMode = FailureMode.NONE

    @property
    def enabled(self) -> bool:
        return self.mode is not FailureMode.NONE

    @property
    def display_name(self) -> str:
        return failure_mode_label(self.mode)

    @property
    def description(self) -> str:
        return failure_mode_description(self.mode)


def normalize_failure_mode(value: str | FailureMode | None) -> FailureMode:
    """
    Normalize an API/UI failure-mode value.

    Empty or missing values mean no simulated failure.
    Unknown values raise ValueError so callers cannot silently select
    an unintended failure mode.
    """

    if value is None:
        return FailureMode.NONE

    if isinstance(value, FailureMode):
        return value

    normalized = value.strip().upper()

    if not normalized:
        return FailureMode.NONE

    try:
        return FailureMode(normalized)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in FailureMode)
        raise ValueError(
            f"Unsupported failure mode '{value}'. "
            f"Expected one of: {allowed}."
        ) from exc


def failure_mode_label(mode: FailureMode) -> str:
    """Human-readable label for the frontend/demo."""

    labels = {
        FailureMode.NONE: "No Failure",
        FailureMode.AI_UNAVAILABLE: "AI Unavailable",
        FailureMode.EVIDENCE_RETRIEVAL_FAILURE: "Evidence Retrieval Failure",
        FailureMode.MALFORMED_AI_OUTPUT: "Malformed AI Output",
        FailureMode.MISSING_ADJUSTMENT_SOURCE: "Missing Adjustment Source",
        FailureMode.DUPLICATE_BANK_RECORD: "Duplicate Bank Record",
        FailureMode.AMBIGUOUS_SETTLEMENT: "Ambiguous Settlement",
    }

    return labels[mode]


def failure_mode_description(mode: FailureMode) -> str:
    """Safe-degradation description shown in observability/UI layers."""

    descriptions = {
        FailureMode.NONE: "No failure is being simulated.",
        FailureMode.AI_UNAVAILABLE: (
            "Investigation AI is unavailable; deterministic controls "
            "must remain operational and affected cases must not be "
            "auto-resolved by the unavailable AI."
        ),
        FailureMode.EVIDENCE_RETRIEVAL_FAILURE: (
            "Evidence retrieval is unavailable; investigation cannot "
            "claim an evidence-backed explanation."
        ),
        FailureMode.MALFORMED_AI_OUTPUT: (
            "The investigation output is malformed; deterministic "
            "validation must reject unsafe output."
        ),
        FailureMode.MISSING_ADJUSTMENT_SOURCE: (
            "The adjustment source is unavailable; the related "
            "hypothesis cannot be treated as proven."
        ),
        FailureMode.DUPLICATE_BANK_RECORD: (
            "A duplicate bank record is present; reconciliation must "
            "surface the ambiguity rather than silently resolving it."
        ),
        FailureMode.AMBIGUOUS_SETTLEMENT: (
            "Settlement matching is ambiguous; the case must remain "
            "unresolved or be routed for controlled review."
        ),
    }

    return descriptions[mode]


def create_failure_simulation(
    value: str | FailureMode | None,
) -> FailureSimulation:
    """Build a validated simulation configuration."""

    return FailureSimulation(mode=normalize_failure_mode(value))
