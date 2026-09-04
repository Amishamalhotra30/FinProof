from datetime import datetime

from app.evidence.graph import EvidenceGraph
from app.reconciliation.graph import ReconciliationGraph
from app.reconciliation.models import (
    Cardinality,
    MatchMethod,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)


class ExactMatcher:
    """
    Deterministic Phase-3 matcher.

    This matcher only creates relationships when the
    relevant identifiers match exactly.

    It never performs fuzzy matching or inference.
    """

    def match(
        self,
        evidence_graph: EvidenceGraph,
    ) -> ReconciliationGraph:

        graph = ReconciliationGraph()

        for node in evidence_graph.nodes.values():
            graph.add_node(
                node.evidence_id,
                node.record,
            )

        payments = self._nodes(
            evidence_graph,
            "payment",
        )

        orders = self._nodes(
            evidence_graph,
            "order",
        )

        refunds = self._nodes(
            evidence_graph,
            "refund",
        )

        fees = self._nodes(
            evidence_graph,
            "fee",
        )

        adjustments = self._nodes(
            evidence_graph,
            "adjustment",
        )

        settlements = self._nodes(
            evidence_graph,
            "settlement",
        )

        bank = self._nodes(
            evidence_graph,
            "bank",
        )

        self._match_orders(
            graph,
            orders,
            payments,
        )

        self._match_payment_children(
            graph,
            payments,
            refunds,
            fees,
            adjustments,
            settlements,
        )

        self._match_bank_settlements(
            graph,
            settlements,
            bank,
        )

        return graph

    @staticmethod
    def _nodes(
        evidence_graph: EvidenceGraph,
        record_type: str,
    ) -> list:

        return [
            node
            for node in evidence_graph.nodes.values()
            if node.record_type == record_type
        ]

    def _match_orders(
        self,
        graph: ReconciliationGraph,
        orders: list,
        payments: list,
    ) -> None:

        payments_by_order = {}

        for payment_node in payments:

            order_id = getattr(
                payment_node.record,
                "order_id",
                None,
            )

            if order_id is None:
                continue

            payments_by_order.setdefault(
                order_id,
                [],
            ).append(payment_node)

        for order_node in orders:

            order_id = getattr(
                order_node.record,
                "order_id",
                None,
            )

            if order_id is None:
                continue

            for payment_node in payments_by_order.get(
                order_id,
                [],
            ):

                self._add_relationship(
                    graph=graph,
                    source=order_node,
                    target=payment_node,
                    relationship_type=(
                        RelationshipType.ORDER_FOR_PAYMENT
                    ),
                    cardinality=(
                        Cardinality.ONE_TO_MANY
                    ),
                    evidence=[
                        "order_id"
                    ],
                )

    def _match_payment_children(
        self,
        graph: ReconciliationGraph,
        payments: list,
        refunds: list,
        fees: list,
        adjustments: list,
        settlements: list,
    ) -> None:

        payment_map = {
            getattr(
                node.record,
                "payment_id",
                None,
            ): node
            for node in payments
        }

        self._match_children(
            graph,
            payment_map,
            refunds,
            RelationshipType.REFUND_FOR_PAYMENT,
            "payment_id",
        )

        self._match_children(
            graph,
            payment_map,
            fees,
            RelationshipType.FEE_FOR_PAYMENT,
            "payment_id",
        )

        self._match_children(
            graph,
            payment_map,
            adjustments,
            RelationshipType.ADJUSTMENT_FOR_PAYMENT,
            "payment_id",
        )

        self._match_children(
            graph,
            payment_map,
            settlements,
            RelationshipType.SETTLEMENT_FOR_PAYMENT,
            "payment_id",
        )

    def _match_children(
        self,
        graph: ReconciliationGraph,
        payment_map: dict,
        children: list,
        relationship_type: RelationshipType,
        reference_field: str,
    ) -> None:

        for child_node in children:

            payment_id = getattr(
                child_node.record,
                reference_field,
                None,
            )

            if payment_id is None:
                continue

            payment_node = payment_map.get(
                payment_id
            )

            if payment_node is None:
                continue

            self._add_relationship(
                graph=graph,
                source=payment_node,
                target=child_node,
                relationship_type=relationship_type,
                cardinality=(
                    Cardinality.ONE_TO_MANY
                ),
                evidence=[
                    reference_field
                ],
            )

    def _match_bank_settlements(
        self,
        graph: ReconciliationGraph,
        settlements: list,
        bank_nodes: list,
    ) -> None:

        bank_by_utr = {}

        for bank_node in bank_nodes:

            utr = getattr(
                bank_node.record,
                "utr",
                None,
            )

            if utr is None:
                continue

            bank_by_utr.setdefault(
                utr,
                [],
            ).append(bank_node)

        for settlement_node in settlements:

            utr = getattr(
                settlement_node.record,
                "utr",
                None,
            )

            if utr is None:
                continue

            for bank_node in bank_by_utr.get(
                utr,
                [],
            ):

                self._add_relationship(
                    graph=graph,
                    source=settlement_node,
                    target=bank_node,
                    relationship_type=(
                        RelationshipType.BANK_FOR_SETTLEMENT
                    ),
                    cardinality=(
                        Cardinality.ONE_TO_MANY
                    ),
                    evidence=[
                        "utr"
                    ],
                )

    @staticmethod
    def _add_relationship(
        graph: ReconciliationGraph,
        source,
        target,
        relationship_type: RelationshipType,
        cardinality: Cardinality,
        evidence: list[str],
    ) -> None:

        relationship_id = (
            f"REL_"
            f"{source.evidence_id}_"
            f"{target.evidence_id}"
        )

        relationship = Relationship(
            relationship_id=relationship_id,
            source_record_id=source.evidence_id,
            target_record_id=target.evidence_id,
            relationship_type=relationship_type,
            cardinality=cardinality,
            method=MatchMethod.EXACT_ID,
            evidence=evidence,
            status=RelationshipStatus.CONFIRMED,
            created_at=datetime.now(),
        )

        graph.add_relationship(
            relationship
        )