from dataclasses import dataclass, field

from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.reconstruction.temporal_orderer import TemporalOrderer


@dataclass
class EventChain:
    """
    A connected sequence of observed financial events.

    A chain contains only events and relationships that already
    exist in the EventGraph.

    It does not infer missing events.
    """

    chain_id: str
    event_ids: list[str] = field(
        default_factory=list
    )

    @property
    def first_event_id(self) -> str | None:
        if not self.event_ids:
            return None

        return self.event_ids[0]

    @property
    def last_event_id(self) -> str | None:
        if not self.event_ids:
            return None

        return self.event_ids[-1]

    @property
    def length(self) -> int:
        return len(self.event_ids)


class EventChainBuilder:
    """
    Builds observed event chains from an EventGraph.

    Responsibilities:
        - preserve existing graph relationships
        - provide deterministic temporal ordering
        - preserve branches
        - preserve disconnected events
        - never fabricate missing events
    """

    def __init__(
        self,
        temporal_orderer: TemporalOrderer | None = None,
    ):
        self.temporal_orderer = (
            temporal_orderer
            or TemporalOrderer()
        )

    def build(
        self,
        graph: EventGraph,
    ) -> list[EventChain]:
        """
        Build connected observed chains.

        Each connected component becomes an EventChain.
        Events within a component are ordered chronologically.

        The original graph is never modified.
        """

        if not graph.events:
            return []

        ordered_events = (
            self.temporal_orderer.order_graph(
                graph
            )
        )

        visited: set[str] = set()
        chains: list[EventChain] = []

        for event in ordered_events:

            if event.event_id in visited:
                continue

            component = self._collect_component(
                graph,
                event.event_id,
            )

            visited.update(component)

            component_events = [
                graph.get_event(event_id)
                for event_id in component
            ]

            component_events = (
                self.temporal_orderer.order(
                    component_events
                )
            )

            chain = EventChain(
                chain_id=self._chain_id(
                    component_events
                ),
                event_ids=[
                    event.event_id
                    for event in component_events
                ],
            )

            chains.append(chain)

        return chains

    def build_event_sequences(
        self,
        graph: EventGraph,
    ) -> list[list[FinancialEvent]]:
        """
        Convenience method returning the actual events
        contained in each observed chain.
        """

        chains = self.build(graph)

        return [
            [
                graph.get_event(event_id)
                for event_id in chain.event_ids
            ]
            for chain in chains
        ]

    @staticmethod
    def _collect_component(
        graph: EventGraph,
        start_event_id: str,
    ) -> set[str]:
        """
        Collect all events connected to the starting event.

        Relationships are treated as graph connectivity for the
        purpose of identifying an observed chain.

        No new relationship is created.
        """

        component: set[str] = set()
        stack = [start_event_id]

        while stack:

            event_id = stack.pop()

            if event_id in component:
                continue

            component.add(event_id)

            event = graph.get_event(
                event_id
            )

            # Forward relationships.
            for related_id in (
                event.related_event_ids
            ):
                if related_id not in component:
                    stack.append(
                        related_id
                    )

            # Reverse relationships.
            #
            # This allows the component to remain intact even
            # when relationships are directed.
            for candidate in graph.events.values():

                if (
                    event_id
                    in candidate.related_event_ids
                    and candidate.event_id
                    not in component
                ):
                    stack.append(
                        candidate.event_id
                    )

        return component

    @staticmethod
    def _chain_id(
        events: list[FinancialEvent],
    ) -> str:

        if not events:
            return "CHAIN_EMPTY"

        event_ids = sorted(
            event.event_id
            for event in events
        )

        return (
            "CHAIN_"
            + "_".join(event_ids)
        )