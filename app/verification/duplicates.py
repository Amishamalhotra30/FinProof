from app.domain.graph import EventGraph
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Severity,
)


def _event_fingerprint(event) -> tuple:
    """
    Build a deterministic identity fingerprint for an observed event.

    event_id is intentionally excluded because two duplicate observations
    may have different identifiers.
    """

    return (
        event.event_type,
        event.entity_id,
        event.amount,
        event.currency,
        event.timestamp,
        event.source,
    )


def check_duplicate_events(
    graph: EventGraph,
) -> ControlCheck:
    """
    Detect semantically duplicate financial events.

    Two events are considered duplicates when their observable
    financial identity is identical, even if their event IDs differ.

    This control does not remove, merge, or repair events.
    """

    fingerprints: dict[tuple, list[str]] = {}

    for event in graph.events.values():

        fingerprint = _event_fingerprint(event)

        fingerprints.setdefault(
            fingerprint,
            [],
        ).append(event.event_id)

    duplicate_event_ids: list[str] = []

    for event_ids in fingerprints.values():

        if len(event_ids) > 1:
            duplicate_event_ids.extend(event_ids)

    if duplicate_event_ids:
        return ControlCheck(
            control_id="DUPLICATE_EVENT",
            control_name="Duplicate event protection",
            status=ControlStatus.FAIL,
            affected_event_ids=list(
                dict.fromkeys(
                    duplicate_event_ids
                )
            ),
            supporting_evidence_ids=[],
            severity=Severity.HIGH,
            blocking=True,
        )

    return ControlCheck(
        control_id="DUPLICATE_EVENT",
        control_name="Duplicate event protection",
        status=ControlStatus.PASS,
        affected_event_ids=[],
        supporting_evidence_ids=[],
        severity=Severity.INFO,
        blocking=False,
    )


def run_duplicate_controls(
    graph: EventGraph,
) -> list[ControlCheck]:
    """
    Run all duplicate-protection controls.
    """

    return [
        check_duplicate_events(graph),
    ]