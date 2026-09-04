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


class NormalizedMatcher:
    """
    Phase 3 normalized deterministic matcher.

    Handles representation differences such as:
        PAY_001
        pay_001
        " PAY_001 "
        PAY-001

    It does not perform fuzzy matching.

    A normalized match is confirmed only when exactly one
    target record has the normalized identifier.
    """

    def match(
        self,
        evidence_graph: EvidenceGraph,
        existing_graph: ReconciliationGraph | None = None,
    ) -> ReconciliationGraph:

        graph = (
            existing_graph
            if existing_graph is not None
            else ReconciliationGraph()
        )

        if existing_graph is None:
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

        banks = self._nodes(
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
            banks,
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

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        normalized = (
            str(value)
            .strip()
            .upper()
            .replace("-", "")
            .replace("_", "")
            .replace(" ", "")
        )

        return normalized or None

    def _match_orders(
        self,
        graph: ReconciliationGraph,
        orders: list,
        payments: list,
    ) -> None:

        orders_by_id = {}

        for order_node in orders:

            order_id = getattr(
                order_node.record,
                "order_id",
                None,
            )

            normalized = self.normalize(
                order_id
            )

            if normalized is None:
                continue

            orders_by_id.setdefault(
                normalized,
                [],
            ).append(order_node)

        for payment_node in payments:

            order_id = getattr(
                payment_node.record,
                "order_id",
                None,
            )

            normalized = self.normalize(
                order_id
            )

            if normalized is None:
                continue

            candidates = orders_by_id.get(
                normalized,
                [],
            )

            if len(candidates) != 1:
                continue

            order_node = candidates[0]

            if self._relationship_exists(
                graph,
                order_node.evidence_id,
                payment_node.evidence_id,
            ):
                continue

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
                    "normalized_order_id"
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

        payments_by_id = {}

        for payment_node in payments:

            payment_id = getattr(
                payment_node.record,
                "payment_id",
                None,
            )

            normalized = self.normalize(
                payment_id
            )

            if normalized is None:
                continue

            payments_by_id.setdefault(
                normalized,
                [],
            ).append(payment_node)

        self._match_children(
            graph,
            payments_by_id,
            refunds,
            RelationshipType.REFUND_FOR_PAYMENT,
            "payment_id",
        )

        self._match_children(
            graph,
            payments_by_id,
            fees,
            RelationshipType.FEE_FOR_PAYMENT,
            "payment_id",
        )

        self._match_children(
            graph,
            payments_by_id,
            adjustments,
            RelationshipType.ADJUSTMENT_FOR_PAYMENT,
            "payment_id",
        )

        self._match_children(
            graph,
            payments_by_id,
            settlements,
            RelationshipType.SETTLEMENT_FOR_PAYMENT,
            "payment_id",
        )

    def _match_children(
        self,
        graph: ReconciliationGraph,
        payments_by_id: dict,
        children: list,
        relationship_type: RelationshipType,
        reference_field: str,
    ) -> None:

        for child_node in children:

            reference = getattr(
                child_node.record,
                reference_field,
                None,
            )

            normalized = self.normalize(
                reference
            )

            if normalized is None:
                continue

            candidates = payments_by_id.get(
                normalized,
                [],
            )

            if len(candidates) != 1:
                continue

            payment_node = candidates[0]

            if self._relationship_exists(
                graph,
                payment_node.evidence_id,
                child_node.evidence_id,
            ):
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
                    f"normalized_{reference_field}"
                ],
            )

    def _match_bank_settlements(
        self,
        graph: ReconciliationGraph,
        settlements: list,
        banks: list,
    ) -> None:

        banks_by_utr = {}

        for bank_node in banks:

            utr = getattr(
                bank_node.record,
                "utr",
                None,
            )

            normalized = self.normalize(
                utr
            )

            if normalized is None:
                continue

            banks_by_utr.setdefault(
                normalized,
                [],
            ).append(bank_node)

        for settlement_node in settlements:

            utr = getattr(
                settlement_node.record,
                "utr",
                None,
            )

            normalized = self.normalize(
                utr
            )

            if normalized is None:
                continue

            candidates = banks_by_utr.get(
                normalized,
                [],
            )

            if len(candidates) != 1:
                continue

            bank_node = candidates[0]

            if self._relationship_exists(
                graph,
                settlement_node.evidence_id,
                bank_node.evidence_id,
            ):
                continue

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
                    "normalized_utr"
                ],
            )

    @staticmethod
    def _relationship_exists(
        graph: ReconciliationGraph,
        source_id: str,
        target_id: str,
    ) -> bool:

        return any(
            relationship.source_record_id
            == source_id
            and relationship.target_record_id
            == target_id
            for relationship
            in graph.relationships
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
            method=MatchMethod.NORMALIZED_ID,
            evidence=evidence,
            status=RelationshipStatus.CONFIRMED,
            created_at=datetime.now(),
        )

        graph.add_relationship(
            relationship
        )