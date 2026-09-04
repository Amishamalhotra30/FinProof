from pydantic import BaseModel, Field

from app.domain.events import FinancialEvent


class EventGraph(BaseModel):
    """
    Domain-level graph of reconstructed financial events.

    Events are nodes and related_event_ids represent directed
    event relationships.

    The graph represents observed/reconstructed structure.
    It does not determine financial correctness.
    """

    events: dict[str, FinancialEvent] = Field(
        default_factory=dict
    )

    def add_event(
        self,
        event: FinancialEvent,
    ) -> None:

        if event.event_id in self.events:
            raise ValueError(
                f"Event already exists: {event.event_id}"
            )

        self.events[event.event_id] = event

    def get_event(
        self,
        event_id: str,
    ) -> FinancialEvent:

        if event_id not in self.events:
            raise KeyError(
                f"Event not found: {event_id}"
            )

        return self.events[event_id]

    def add_relationship(
        self,
        event_id: str,
        related_event_id: str,
    ) -> None:

        event = self.get_event(
            event_id
        )

        if related_event_id not in self.events:
            raise KeyError(
                f"Related event not found: "
                f"{related_event_id}"
            )

        if (
            related_event_id
            not in event.related_event_ids
        ):
            event.related_event_ids.append(
                related_event_id
            )

    def ordered_events(
        self,
    ) -> list[FinancialEvent]:

        return sorted(
            self.events.values(),
            key=lambda event: event.timestamp,
        )

    @property
    def node_count(self) -> int:
        """
        Number of event nodes in the graph.
        """

        return len(self.events)

    @property
    def relationship_count(self) -> int:
        """
        Number of directed event relationships.

        Each source -> target relationship is counted once.
        """

        return sum(
            len(event.related_event_ids)
            for event in self.events.values()
        )