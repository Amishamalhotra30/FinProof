from app.domain.enums import EventType
from app.domain.graph import EventGraph
from app.reconstruction.event_chain import EventChain
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Severity,
)


def _ordering_is_valid(
    source,
    target,
) -> bool:
    """
    Determine whether two related financial events respect
    their known chronological lifecycle.

    related_event_ids represent relationships between events.
    They do not necessarily represent chronological direction.

    Only lifecycle relationships with an explicitly known
    temporal constraint are checked.
    """

    source_type = source.event_type
    target_type = target.event_type

    settlement_types = {
        EventType.SETTLEMENT_CREATED,
        EventType.SETTLEMENT_PROCESSED,
    }

    # ------------------------------------------------------------
    # Payment must occur before settlement.
    # ------------------------------------------------------------

    if (
        source_type == EventType.PAYMENT_CAPTURED
        and target_type in settlement_types
    ):
        return (
            source.timestamp
            <= target.timestamp
        )

    if (
        source_type in settlement_types
        and target_type == EventType.PAYMENT_CAPTURED
    ):
        return (
            target.timestamp
            <= source.timestamp
        )

    # ------------------------------------------------------------
    # Payment must occur before refund creation.
    # ------------------------------------------------------------

    if (
        source_type == EventType.PAYMENT_CAPTURED
        and target_type == EventType.REFUND_CREATED
    ):
        return (
            source.timestamp
            <= target.timestamp
        )

    if (
        source_type == EventType.REFUND_CREATED
        and target_type == EventType.PAYMENT_CAPTURED
    ):
        return (
            target.timestamp
            <= source.timestamp
        )

    # ------------------------------------------------------------
    # Settlement must occur before bank credit.
    # ------------------------------------------------------------

    if (
        source_type in settlement_types
        and target_type == EventType.BANK_CREDIT
    ):
        return (
            source.timestamp
            <= target.timestamp
        )

    if (
        source_type == EventType.BANK_CREDIT
        and target_type in settlement_types
    ):
        return (
            target.timestamp
            <= source.timestamp
        )

    # ------------------------------------------------------------
    # Unknown relationship type:
    #
    # Do not impose an arbitrary temporal rule.
    # ------------------------------------------------------------

    return True


def check_event_ordering(
    graph: EventGraph,
) -> ControlCheck:
    """
    Verify that known financial event relationships respect
    their semantic chronological ordering.

    This does not assume that the direction of
    related_event_ids is the chronological direction.
    """

    affected_event_ids: list[str] = []

    for source in graph.events.values():

        for target_id in source.related_event_ids:

            target = graph.get_event(
                target_id
            )

            if not _ordering_is_valid(
                source,
                target,
            ):
                affected_event_ids.extend(
                    [
                        source.event_id,
                        target.event_id,
                    ]
                )

    if affected_event_ids:

        return ControlCheck(
            control_id="EVENT_ORDERING",
            control_name="Event ordering",
            status=ControlStatus.FAIL,
            expected_value=None,
            observed_value=None,
            difference=None,
            affected_event_ids=list(
                dict.fromkeys(
                    affected_event_ids
                )
            ),
            supporting_evidence_ids=[],
            severity=Severity.HIGH,
            blocking=True,
        )

    return ControlCheck(
        control_id="EVENT_ORDERING",
        control_name="Event ordering",
        status=ControlStatus.PASS,
        severity=Severity.INFO,
        blocking=False,
    )


def _settlement_payment_pairs(
    graph: EventGraph,
    chains: list[EventChain],
):
    """
    Produce settlement/payment pairs within reconstructed
    event chains.

    Some benchmark settlement records do not retain a direct
    settlement → payment relationship after reconstruction.
    The chain itself still establishes that the events belong
    to the same financial lifecycle.

    Therefore settlement timing is evaluated within each
    chain rather than relying exclusively on
    related_event_ids.
    """

    settlement_types = {
        EventType.SETTLEMENT_CREATED,
        EventType.SETTLEMENT_PROCESSED,
    }

    for chain in chains:

        events = [
            graph.get_event(event_id)
            for event_id in chain.event_ids
        ]

        payments = [
            event
            for event in events
            if event.event_type
            == EventType.PAYMENT_CAPTURED
        ]

        settlements = [
            event
            for event in events
            if event.event_type
            in settlement_types
        ]

        for settlement in settlements:

            for payment in payments:

                yield settlement, payment


def check_settlement_timing(
    graph: EventGraph,
    chains: list[EventChain] | None = None,
) -> ControlCheck:
    """
    Verify that settlement events do not occur before the
    payment events belonging to the same reconstructed chain.

    The primary lifecycle rule is:

        PAYMENT_CAPTURED <= SETTLEMENT

    Direct relationships are used when available, while
    reconstructed chain membership is used as the fallback
    when the relationship graph does not preserve a direct
    settlement → payment edge.
    """

    affected_event_ids: list[str] = []

    # ------------------------------------------------------------
    # Preserve compatibility with existing callers/tests that
    # provide only an EventGraph.
    #
    # In that case, use direct relationships exactly as before.
    # ------------------------------------------------------------

    if chains is None:

        settlement_types = {
            EventType.SETTLEMENT_CREATED,
            EventType.SETTLEMENT_PROCESSED,
        }

        for settlement in graph.events.values():

            if settlement.event_type not in settlement_types:
                continue

            for related_id in settlement.related_event_ids:

                related = graph.get_event(
                    related_id
                )

                if (
                    related.event_type
                    == EventType.PAYMENT_CAPTURED
                    and settlement.timestamp
                    < related.timestamp
                ):
                    affected_event_ids.extend(
                        [
                            settlement.event_id,
                            related.event_id,
                        ]
                    )

    else:

        # --------------------------------------------------------
        # Evaluate settlement/payment ordering inside every
        # reconstructed chain.
        # --------------------------------------------------------

        for settlement, payment in _settlement_payment_pairs(
            graph,
            chains,
        ):

            if settlement.timestamp < payment.timestamp:

                affected_event_ids.extend(
                    [
                        settlement.event_id,
                        payment.event_id,
                    ]
                )

    if affected_event_ids:

        return ControlCheck(
            control_id="SETTLEMENT_TIMING",
            control_name="Settlement timing",
            status=ControlStatus.FAIL,
            affected_event_ids=list(
                dict.fromkeys(
                    affected_event_ids
                )
            ),
            severity=Severity.HIGH,
            blocking=True,
        )

    return ControlCheck(
        control_id="SETTLEMENT_TIMING",
        control_name="Settlement timing",
        status=ControlStatus.PASS,
        severity=Severity.INFO,
        blocking=False,
    )


def check_bank_after_settlement(
    graph: EventGraph,
) -> ControlCheck:
    """
    Verify that bank-credit events do not occur before the
    settlement event they are related to.
    """

    affected_event_ids: list[str] = []

    settlement_types = {
        EventType.SETTLEMENT_CREATED,
        EventType.SETTLEMENT_PROCESSED,
    }

    for settlement in graph.events.values():

        if settlement.event_type not in settlement_types:
            continue

        for related_id in settlement.related_event_ids:

            bank = graph.get_event(
                related_id
            )

            if (
                bank.event_type
                == EventType.BANK_CREDIT
                and bank.timestamp
                < settlement.timestamp
            ):
                affected_event_ids.extend(
                    [
                        settlement.event_id,
                        bank.event_id,
                    ]
                )

    if affected_event_ids:

        return ControlCheck(
            control_id="BANK_AFTER_SETTLEMENT",
            control_name="Bank after settlement",
            status=ControlStatus.FAIL,
            affected_event_ids=list(
                dict.fromkeys(
                    affected_event_ids
                )
            ),
            severity=Severity.HIGH,
            blocking=True,
        )

    return ControlCheck(
        control_id="BANK_AFTER_SETTLEMENT",
        control_name="Bank after settlement",
        status=ControlStatus.PASS,
        severity=Severity.INFO,
        blocking=False,
    )


def check_chain_temporal_order(
    graph: EventGraph,
    chains: list[EventChain],
) -> ControlCheck:
    """
    Verify that every EventChain is internally ordered
    chronologically.
    """

    affected_event_ids: list[str] = []

    for chain in chains:

        timestamps = [
            graph.get_event(
                event_id
            ).timestamp
            for event_id in chain.event_ids
        ]

        for index in range(
            1,
            len(timestamps),
        ):

            if (
                timestamps[index]
                < timestamps[index - 1]
            ):
                affected_event_ids.extend(
                    [
                        chain.event_ids[
                            index - 1
                        ],
                        chain.event_ids[
                            index
                        ],
                    ]
                )

    if affected_event_ids:

        return ControlCheck(
            control_id="CHAIN_TEMPORAL_ORDER",
            control_name="Chain temporal order",
            status=ControlStatus.FAIL,
            affected_event_ids=list(
                dict.fromkeys(
                    affected_event_ids
                )
            ),
            severity=Severity.HIGH,
            blocking=True,
        )

    return ControlCheck(
        control_id="CHAIN_TEMPORAL_ORDER",
        control_name="Chain temporal order",
        status=ControlStatus.PASS,
        severity=Severity.INFO,
        blocking=False,
    )


def run_temporal_controls(
    graph: EventGraph,
    chains: list[EventChain],
) -> list[ControlCheck]:
    """
    Run all currently implemented temporal controls.

    No control mutates the supplied graph or chains.
    """

    return [
        check_event_ordering(graph),
        check_settlement_timing(
            graph,
            chains,
        ),
        check_bank_after_settlement(graph),
        check_chain_temporal_order(
            graph,
            chains,
        ),
    ]