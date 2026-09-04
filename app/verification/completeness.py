from app.domain.enums import EventType
from app.domain.graph import EventGraph
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Severity,
)


SETTLEMENT_TYPES = {
    EventType.SETTLEMENT_CREATED,
    EventType.SETTLEMENT_PROCESSED,
}


def _has_related_event_type(
    graph: EventGraph,
    event,
    event_type: EventType,
) -> bool:
    """
    Check whether an event has a directly related event
    of the requested type.
    """

    for related_id in event.related_event_ids:

        related_event = graph.get_event(
            related_id
        )

        if related_event is None:
            continue

        if related_event.event_type == event_type:
            return True

    return False


def _has_payment_reference(
    graph: EventGraph,
    event,
) -> bool:
    """
    Check whether an event is related to a payment.

    The preferred representation is the explicit event
    relationship. This helper also handles graphs where the
    relationship is represented from the payment side.
    """

    # --------------------------------------------------------
    # First: normal direct relationship
    # --------------------------------------------------------

    if _has_related_event_type(
        graph,
        event,
        EventType.PAYMENT_CAPTURED,
    ):
        return True

    # --------------------------------------------------------
    # Second: reverse relationship.
    #
    # Some graph builders attach the refund to the payment,
    # while the refund itself does not contain the payment
    # event ID in related_event_ids.
    # --------------------------------------------------------

    for candidate in graph.events.values():

        if candidate.event_type != (
            EventType.PAYMENT_CAPTURED
        ):
            continue

        if event.event_id in candidate.related_event_ids:
            return True

    return False


def check_payment_has_settlement(
    graph: EventGraph,
) -> ControlCheck:
    """
    Verify that every observed payment has corresponding
    settlement evidence.

    Missing settlement evidence is reported as a failed
    completeness control. No missing event is fabricated.
    """

    affected_event_ids: list[str] = []

    for payment in graph.events.values():

        if payment.event_type != (
            EventType.PAYMENT_CAPTURED
        ):
            continue

        has_settlement = any(
            related_id in graph.events
            and graph.get_event(
                related_id
            ).event_type in SETTLEMENT_TYPES
            for related_id in payment.related_event_ids
        )

        if not has_settlement:
            affected_event_ids.append(
                payment.event_id
            )

    if affected_event_ids:
        return ControlCheck(
            control_id="PAYMENT_SETTLEMENT_COMPLETENESS",
            control_name="Payment settlement completeness",
            status=ControlStatus.FAIL,
            affected_event_ids=affected_event_ids,
            severity=Severity.HIGH,
            blocking=True,
        )

    return ControlCheck(
        control_id="PAYMENT_SETTLEMENT_COMPLETENESS",
        control_name="Payment settlement completeness",
        status=ControlStatus.PASS,
        severity=Severity.INFO,
        blocking=False,
    )


def check_settlement_has_bank_credit(
    graph: EventGraph,
) -> ControlCheck:
    """
    Verify that every observed settlement has corresponding
    bank-credit evidence.

    This checks observable evidence only and does not infer
    why bank evidence may be absent.
    """

    affected_event_ids: list[str] = []

    for settlement in graph.events.values():

        if settlement.event_type not in SETTLEMENT_TYPES:
            continue

        has_bank_credit = any(
            related_id in graph.events
            and graph.get_event(
                related_id
            ).event_type == EventType.BANK_CREDIT
            for related_id in settlement.related_event_ids
        )

        if not has_bank_credit:
            affected_event_ids.append(
                settlement.event_id
            )

    if affected_event_ids:
        return ControlCheck(
            control_id="SETTLEMENT_BANK_COMPLETENESS",
            control_name="Settlement bank-credit completeness",
            status=ControlStatus.FAIL,
            affected_event_ids=affected_event_ids,
            severity=Severity.HIGH,
            blocking=True,
        )

    return ControlCheck(
        control_id="SETTLEMENT_BANK_COMPLETENESS",
        control_name="Settlement bank-credit completeness",
        status=ControlStatus.PASS,
        severity=Severity.INFO,
        blocking=False,
    )


def check_refund_has_payment(
    graph: EventGraph,
) -> ControlCheck:
    """
    Verify that every observed refund has corresponding
    payment evidence.

    The check accepts either direction of the graph
    relationship because the semantic invariant is:

        refund -> payment

    regardless of which direction the graph builder stored
    the edge.
    """

    affected_event_ids: list[str] = []

    for refund in graph.events.values():

        if refund.event_type != (
            EventType.REFUND_CREATED
        ):
            continue

        if not _has_payment_reference(
            graph,
            refund,
        ):
            affected_event_ids.append(
                refund.event_id
            )

    if affected_event_ids:
        return ControlCheck(
            control_id="REFUND_PAYMENT_COMPLETENESS",
            control_name="Refund payment completeness",
            status=ControlStatus.FAIL,
            affected_event_ids=affected_event_ids,
            severity=Severity.MEDIUM,
            blocking=True,
        )

    return ControlCheck(
        control_id="REFUND_PAYMENT_COMPLETENESS",
        control_name="Refund payment completeness",
        status=ControlStatus.PASS,
        severity=Severity.INFO,
        blocking=False,
    )


def run_completeness_controls(
    graph: EventGraph,
) -> list[ControlCheck]:
    """
    Run all currently implemented completeness controls.

    These controls inspect observed relationships only.
    They do not create or infer missing events.
    """

    return [
        check_payment_has_settlement(graph),
        check_settlement_has_bank_credit(graph),
        check_refund_has_payment(graph),
    ]