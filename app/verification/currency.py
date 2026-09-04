from app.domain.graph import EventGraph
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Severity,
)


def check_currency_consistency(
    graph: EventGraph,
) -> ControlCheck:
    """
    Verify that all reconstructed financial events use one
    consistent currency.

    This control does not perform currency conversion and does
    not infer exchange rates.

    If multiple currencies are observed in the same reconstructed
    graph, the control fails.
    """

    currencies: dict[str, list[str]] = {}

    for event in graph.events.values():
        currency = event.currency

        currencies.setdefault(
            currency,
            [],
        ).append(event.event_id)

    if len(currencies) <= 1:
        return ControlCheck(
            control_id="CURRENCY_CONSISTENCY",
            control_name="Currency consistency",
            status=ControlStatus.PASS,
            affected_event_ids=[],
            supporting_evidence_ids=[],
            severity=Severity.INFO,
            blocking=False,
        )

    affected_event_ids: list[str] = []

    for event_ids in currencies.values():
        affected_event_ids.extend(event_ids)

    return ControlCheck(
        control_id="CURRENCY_CONSISTENCY",
        control_name="Currency consistency",
        status=ControlStatus.FAIL,
        affected_event_ids=list(
            dict.fromkeys(affected_event_ids)
        ),
        supporting_evidence_ids=[],
        severity=Severity.HIGH,
        blocking=True,
    )


def run_currency_controls(
    graph: EventGraph,
) -> list[ControlCheck]:
    """
    Run all currency-consistency controls.
    """

    return [
        check_currency_consistency(graph),
    ]