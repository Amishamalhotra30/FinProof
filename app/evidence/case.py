from dataclasses import dataclass

from app.evidence.graph import (
    EvidenceEdge,
    EvidenceGraph,
    EvidenceNode,
)


@dataclass(frozen=True)
class CaseEvidence:
    case_id: str
    root: EvidenceNode
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]

    def nodes_by_type(
        self,
        record_type: str,
    ) -> list[EvidenceNode]:

        return [
            node
            for node in self.nodes
            if node.record_type == record_type
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


class CaseEvidenceAssembler:

    def build(
        self,
        graph: EvidenceGraph,
        payment_id: str,
    ) -> CaseEvidence:

        payment_node = self._find_payment(
            graph,
            payment_id,
        )

        if payment_node is None:
            raise ValueError(
                f"Payment not found: {payment_id}"
            )

        related_ids = {
            payment_node.evidence_id
        }

        edges: list[EvidenceEdge] = []

        for edge in graph.edges:

            if (
                edge.source_id
                == payment_node.evidence_id
                or edge.target_id
                == payment_node.evidence_id
            ):
                edges.append(edge)

                related_ids.add(
                    edge.source_id
                )

                related_ids.add(
                    edge.target_id
                )

        # Include the next level of evidence.
        # This is needed for:
        #
        # PAYMENT
        #    ↓
        # SETTLEMENT
        #    ↓
        # BANK
        #
        # The bank node is not directly connected
        # to the payment.

        first_level_ids = set(
            related_ids
        )

        for edge in graph.edges:

            if (
                edge.source_id
                in first_level_ids
                or edge.target_id
                in first_level_ids
            ):

                if edge not in edges:
                    edges.append(edge)

                related_ids.add(
                    edge.source_id
                )

                related_ids.add(
                    edge.target_id
                )

        nodes = [
            graph.nodes[evidence_id]
            for evidence_id in related_ids
            if evidence_id in graph.nodes
        ]

        nodes.sort(
            key=lambda node: (
                node.record_type,
                node.evidence_id,
            )
        )

        edges.sort(
            key=lambda edge: (
                edge.source_id,
                edge.target_id,
                edge.relationship,
            )
        )

        return CaseEvidence(
            case_id=payment_id,
            root=payment_node,
            nodes=nodes,
            edges=edges,
        )

    @staticmethod
    def _find_payment(
        graph: EvidenceGraph,
        payment_id: str,
    ) -> EvidenceNode | None:

        for node in graph.nodes.values():

            if node.record_type != "payment":
                continue

            record = node.record

            if (
                getattr(
                    record,
                    "payment_id",
                    None,
                )
                == payment_id
            ):
                return node

        return None