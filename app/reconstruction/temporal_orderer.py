from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph


class TemporalOrderer:
    """
    Orders reconstructed events according to their observed
    timestamps.

    This component does not infer event order from financial
    expectations and does not create or modify events.
    """

    def order(
        self,
        events: list[FinancialEvent],
    ) -> list[FinancialEvent]:
        """
        Return events in deterministic chronological order.

        The original list is not modified.
        """

        return sorted(
            events,
            key=self._sort_key,
        )

    def order_graph(
        self,
        graph: EventGraph,
    ) -> list[FinancialEvent]:
        """
        Return the events from an EventGraph in chronological order.

        The graph itself is not modified.
        """

        return self.order(
            list(graph.events.values())
        )

    @staticmethod
    def _sort_key(
        event: FinancialEvent,
    ) -> tuple:
        """
        Sort primarily by observed timestamp.

        event_id is used as a deterministic tie-breaker when
        two events have exactly the same timestamp.
        """

        return (
            event.timestamp,
            event.event_id,
        )