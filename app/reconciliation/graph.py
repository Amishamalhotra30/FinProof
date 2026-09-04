from dataclasses import dataclass, field

from app.reconciliation.models import Relationship


@dataclass
class ReconciliationGraph:
    """
    Relationship graph for Phase 3 reconciliation.

    The graph stores records as nodes and the relationships
    discovered between those records as edges.

    It does not decide financial correctness.
    It only represents evidence relationships.
    """

    nodes: dict[str, object] = field(
        default_factory=dict
    )

    relationships: list[Relationship] = field(
        default_factory=list
    )

    def add_node(
        self,
        record_id: str,
        record: object,
    ) -> None:

        self.nodes[record_id] = record

    def add_relationship(
        self,
        relationship: Relationship,
    ) -> None:

        self.relationships.append(
            relationship
        )

    def get_node(
        self,
        record_id: str,
    ) -> object | None:

        return self.nodes.get(record_id)

    def get_relationships(
        self,
        record_id: str,
    ) -> list[Relationship]:

        return [
            relationship
            for relationship in self.relationships
            if (
                relationship.source_record_id
                == record_id
                or relationship.target_record_id
                == record_id
            )
        ]

    def relationships_from(
        self,
        record_id: str,
    ) -> list[Relationship]:

        return [
            relationship
            for relationship in self.relationships
            if (
                relationship.source_record_id
                == record_id
            )
        ]

    def relationships_to(
        self,
        record_id: str,
    ) -> list[Relationship]:

        return [
            relationship
            for relationship in self.relationships
            if (
                relationship.target_record_id
                == record_id
            )
        ]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def relationship_count(self) -> int:
        return len(self.relationships)