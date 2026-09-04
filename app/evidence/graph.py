from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvidenceNode:
    evidence_id: str
    record_type: str
    record: object


@dataclass(frozen=True)
class EvidenceEdge:
    source_id: str
    target_id: str
    relationship: str


@dataclass
class EvidenceGraph:
    nodes: dict[str, EvidenceNode] = field(
        default_factory=dict
    )

    edges: list[EvidenceEdge] = field(
        default_factory=list
    )

    def add_node(
        self,
        evidence_id: str,
        record_type: str,
        record: object,
    ) -> None:

        if evidence_id in self.nodes:
            raise ValueError(
                f"Duplicate evidence ID: {evidence_id}"
            )

        self.nodes[evidence_id] = EvidenceNode(
            evidence_id=evidence_id,
            record_type=record_type,
            record=record,
        )

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
    ) -> None:

        if source_id not in self.nodes:
            raise ValueError(
                f"Unknown source evidence: {source_id}"
            )

        if target_id not in self.nodes:
            raise ValueError(
                f"Unknown target evidence: {target_id}"
            )

        self.edges.append(
            EvidenceEdge(
                source_id=source_id,
                target_id=target_id,
                relationship=relationship,
            )
        )

    def get_node(
        self,
        evidence_id: str,
    ) -> EvidenceNode | None:

        return self.nodes.get(evidence_id)

    def related_nodes(
        self,
        evidence_id: str,
    ) -> list[EvidenceNode]:

        related_ids: list[str] = []

        for edge in self.edges:

            if edge.source_id == evidence_id:
                related_ids.append(
                    edge.target_id
                )

            elif edge.target_id == evidence_id:
                related_ids.append(
                    edge.source_id
                )

        return [
            self.nodes[node_id]
            for node_id in related_ids
        ]

    def relationships_for(
        self,
        evidence_id: str,
    ) -> list[EvidenceEdge]:

        return [
            edge
            for edge in self.edges
            if (
                edge.source_id == evidence_id
                or edge.target_id == evidence_id
            )
        ]

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)