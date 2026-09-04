from dataclasses import dataclass

from app.reconciliation.graph import (
    ReconciliationGraph,
)
from app.reconciliation.models import (
    RelationshipStatus,
    RelationshipType,
)


class GraphFindingType:
    MISSING_SETTLEMENT = "MISSING_SETTLEMENT"
    MISSING_BANK_CREDIT = "MISSING_BANK_CREDIT"
    MULTIPLE_SETTLEMENTS = "MULTIPLE_SETTLEMENTS"
    UNRESOLVED_RELATIONSHIP = (
        "UNRESOLVED_RELATIONSHIP"
    )


@dataclass(frozen=True)
class GraphFinding:
    case_id: str
    finding_type: str
    severity: str
    message: str
    evidence: list[str]


class GraphReasoner:
    """
    Deterministic reasoning over the reconciliation graph.

    The reasoner is read-only. It inspects the graph and
    reports structural inconsistencies in the evidence chain.

    Expected financial chain:

        PAYMENT
            |
            v
        SETTLEMENT
            |
            v
          BANK

    The reasoner does not create or modify relationships.
    """

    def reason(
        self,
        graph: ReconciliationGraph,
    ) -> list[GraphFinding]:

        findings: list[GraphFinding] = []

        findings.extend(
            self._find_unresolved_relationships(
                graph
            )
        )

        findings.extend(
            self._find_missing_settlements(
                graph
            )
        )

        findings.extend(
            self._find_missing_bank_credits(
                graph
            )
        )

        findings.extend(
            self._find_multiple_settlements(
                graph
            )
        )

        return findings

    # =========================================================
    # Unresolved relationships
    # =========================================================

    def _find_unresolved_relationships(
        self,
        graph: ReconciliationGraph,
    ) -> list[GraphFinding]:

        findings: list[GraphFinding] = []

        for relationship in graph.relationships:

            if (
                relationship.status
                == RelationshipStatus.CONFIRMED
            ):
                continue

            findings.append(
                GraphFinding(
                    case_id=(
                        relationship.source_record_id
                    ),
                    finding_type=(
                        GraphFindingType
                        .UNRESOLVED_RELATIONSHIP
                    ),
                    severity="MEDIUM",
                    message=(
                        "Relationship is not "
                        "confirmed"
                    ),
                    evidence=list(
                        relationship.evidence
                    ),
                )
            )

        return findings

    # =========================================================
    # Missing settlement
    # =========================================================

    def _find_missing_settlements(
        self,
        graph: ReconciliationGraph,
    ) -> list[GraphFinding]:

        findings: list[GraphFinding] = []

        payment_ids = (
            self._record_ids_by_type(
                graph,
                "payment",
            )
        )

        for payment_id in payment_ids:

            relationships = (
                self._settlement_relationships_for_payment(
                    graph,
                    payment_id,
                )
            )

            if relationships:
                continue

            findings.append(
                GraphFinding(
                    case_id=payment_id,
                    finding_type=(
                        GraphFindingType
                        .MISSING_SETTLEMENT
                    ),
                    severity="HIGH",
                    message=(
                        "Payment has no "
                        "settlement relationship"
                    ),
                    evidence=[
                        f"Payment: {payment_id}"
                    ],
                )
            )

        return findings

    # =========================================================
    # Missing bank credit
    # =========================================================

    def _find_missing_bank_credits(
        self,
        graph: ReconciliationGraph,
    ) -> list[GraphFinding]:

        findings: list[GraphFinding] = []

        settlement_ids = (
            self._record_ids_by_type(
                graph,
                "settlement",
            )
        )

        for settlement_id in settlement_ids:

            relationships = (
                self._bank_relationships_for_settlement(
                    graph,
                    settlement_id,
                )
            )

            if relationships:
                continue

            findings.append(
                GraphFinding(
                    case_id=settlement_id,
                    finding_type=(
                        GraphFindingType
                        .MISSING_BANK_CREDIT
                    ),
                    severity="HIGH",
                    message=(
                        "Settlement has no "
                        "bank credit relationship"
                    ),
                    evidence=[
                        f"Settlement: "
                        f"{settlement_id}"
                    ],
                )
            )

        return findings

    # =========================================================
    # Multiple settlements
    # =========================================================

    def _find_multiple_settlements(
        self,
        graph: ReconciliationGraph,
    ) -> list[GraphFinding]:

        findings: list[GraphFinding] = []

        payment_ids = (
            self._record_ids_by_type(
                graph,
                "payment",
            )
        )

        for payment_id in payment_ids:

            relationships = (
                self._settlement_relationships_for_payment(
                    graph,
                    payment_id,
                )
            )

            if len(relationships) <= 1:
                continue

            settlement_ids = [
                self._other_record_id(
                    relationship,
                    payment_id,
                )
                for relationship
                in relationships
            ]

            findings.append(
                GraphFinding(
                    case_id=payment_id,
                    finding_type=(
                        GraphFindingType
                        .MULTIPLE_SETTLEMENTS
                    ),
                    severity="HIGH",
                    message=(
                        "Payment has multiple "
                        "settlement relationships"
                    ),
                    evidence=settlement_ids,
                )
            )

        return findings

    # =========================================================
    # Settlement relationship lookup
    # =========================================================

    @classmethod
    def _settlement_relationships_for_payment(
        cls,
        graph: ReconciliationGraph,
        payment_id: str,
    ) -> list:

        relationships = []

        for relationship in graph.relationships:

            if (
                relationship.relationship_type
                != RelationshipType
                .SETTLEMENT_FOR_PAYMENT
            ):
                continue

            source_id = (
                relationship.source_record_id
            )

            target_id = (
                relationship.target_record_id
            )

            # -------------------------------------------------
            # Normal logical-ID relationship.
            #
            # Example:
            #
            # SET_001 -> PAY_001
            #
            # or
            #
            # PAY_001 -> SET_001
            # -------------------------------------------------

            if (
                source_id == payment_id
                or target_id == payment_id
            ):
                relationships.append(
                    relationship
                )
                continue

            # -------------------------------------------------
            # Evidence-ID relationship.
            #
            # The graph may store evidence IDs rather than
            # logical financial IDs.
            # -------------------------------------------------

            source = graph.get_node(
                source_id
            )

            target = graph.get_node(
                target_id
            )

            source_type = cls._record_type(
                source
            )

            target_type = cls._record_type(
                target
            )

            if (
                source_type == "payment"
                and getattr(
                    source,
                    "payment_id",
                    None,
                ) == payment_id
                and target_type == "settlement"
            ):
                relationships.append(
                    relationship
                )
                continue

            if (
                target_type == "payment"
                and getattr(
                    target,
                    "payment_id",
                    None,
                ) == payment_id
                and source_type == "settlement"
            ):
                relationships.append(
                    relationship
                )

        return relationships

    # =========================================================
    # Bank relationship lookup
    # =========================================================

    @classmethod
    def _bank_relationships_for_settlement(
        cls,
        graph: ReconciliationGraph,
        settlement_id: str,
    ) -> list:

        relationships = []

        for relationship in graph.relationships:

            if (
                relationship.relationship_type
                != RelationshipType
                .BANK_FOR_SETTLEMENT
            ):
                continue

            source_id = (
                relationship.source_record_id
            )

            target_id = (
                relationship.target_record_id
            )

            if (
                source_id == settlement_id
                or target_id == settlement_id
            ):
                relationships.append(
                    relationship
                )
                continue

            source = graph.get_node(
                source_id
            )

            target = graph.get_node(
                target_id
            )

            source_type = cls._record_type(
                source
            )

            target_type = cls._record_type(
                target
            )

            if (
                source_type == "settlement"
                and getattr(
                    source,
                    "settlement_id",
                    None,
                ) == settlement_id
                and target_type == "bank"
            ):
                relationships.append(
                    relationship
                )
                continue

            if (
                target_type == "settlement"
                and getattr(
                    target,
                    "settlement_id",
                    None,
                ) == settlement_id
                and source_type == "bank"
            ):
                relationships.append(
                    relationship
                )

        return relationships

    # =========================================================
    # Get opposite endpoint
    # =========================================================

    @staticmethod
    def _other_record_id(
        relationship,
        known_record_id: str,
    ) -> str:

        if (
            relationship.source_record_id
            == known_record_id
        ):
            return relationship.target_record_id

        return relationship.source_record_id

    # =========================================================
    # Record type
    # =========================================================

    @staticmethod
    def _record_type(
        record: object | None,
    ) -> str | None:

        if record is None:
            return None

        type_map = {
            "CanonicalOrder": "order",
            "CanonicalPayment": "payment",
            "CanonicalRefund": "refund",
            "CanonicalFee": "fee",
            "CanonicalAdjustment": "adjustment",
            "CanonicalSettlement": "settlement",
            "CanonicalBankEntry": "bank",
        }

        return type_map.get(
            record.__class__.__name__
        )

    # =========================================================
    # Logical record IDs
    # =========================================================

    @staticmethod
    def _record_ids_by_type(
        graph: ReconciliationGraph,
        record_type: str,
    ) -> list[str]:

        expected_class = {
            "order": "CanonicalOrder",
            "payment": "CanonicalPayment",
            "refund": "CanonicalRefund",
            "fee": "CanonicalFee",
            "adjustment": "CanonicalAdjustment",
            "settlement": "CanonicalSettlement",
            "bank": "CanonicalBankEntry",
        }.get(record_type)

        if expected_class is None:
            return []

        id_field = {
            "order": "order_id",
            "payment": "payment_id",
            "refund": "refund_id",
            "fee": "fee_id",
            "adjustment": "event_id",
            "settlement": "settlement_id",
            "bank": "transaction_id",
        }[record_type]

        result: list[str] = []

        for record in graph.nodes.values():

            if (
                record.__class__.__name__
                != expected_class
            ):
                continue

            record_id = getattr(
                record,
                id_field,
                None,
            )

            if record_id is not None:
                result.append(
                    record_id
                )

        return result