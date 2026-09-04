from dataclasses import dataclass
from decimal import Decimal

from app.evidence.graph import EvidenceGraph


@dataclass(frozen=True)
class CandidateFeatures:
    amount_difference: Decimal | None = None
    time_difference_seconds: float | None = None
    reference_match: bool = False
    utr_match: bool = False


@dataclass(frozen=True)
class RelationshipCandidate:
    source_record_id: str
    target_record_id: str
    relationship_type: str
    features: CandidateFeatures


class CandidateGenerator:
    """
    Generates plausible relationship candidates.

    Candidates are NOT confirmed relationships.
    This layer only narrows the search space for later
    deterministic ambiguity handling / AI-assisted matching.
    """

    def generate(
        self,
        evidence_graph: EvidenceGraph,
    ) -> list[RelationshipCandidate]:

        candidates: list[
            RelationshipCandidate
        ] = []

        payments = self._nodes(
            evidence_graph,
            "payment",
        )

        settlements = self._nodes(
            evidence_graph,
            "settlement",
        )

        banks = self._nodes(
            evidence_graph,
            "bank",
        )

        candidates.extend(
            self._payment_settlement_candidates(
                payments,
                settlements,
            )
        )

        candidates.extend(
            self._settlement_bank_candidates(
                settlements,
                banks,
            )
        )

        return candidates

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

    def _payment_settlement_candidates(
        self,
        payments: list,
        settlements: list,
    ) -> list[RelationshipCandidate]:

        candidates = []

        for payment_node in payments:

            payment = payment_node.record

            for settlement_node in settlements:

                settlement = settlement_node.record

                amount_difference = abs(
                    payment.amount
                    - settlement.net_amount
                )

                time_difference = abs(
                    (
                        settlement.event_timestamp
                        - payment.event_timestamp
                    ).total_seconds()
                )

                reference_match = (
                    self._normalize(
                        getattr(
                            settlement,
                            "payment_id",
                            None,
                        )
                    )
                    == self._normalize(
                        getattr(
                            payment,
                            "payment_id",
                            None,
                        )
                    )
                )

                candidates.append(
                    RelationshipCandidate(
                        source_record_id=(
                            payment_node.evidence_id
                        ),
                        target_record_id=(
                            settlement_node.evidence_id
                        ),
                        relationship_type=(
                            "SETTLEMENT_FOR_PAYMENT"
                        ),
                        features=CandidateFeatures(
                            amount_difference=(
                                amount_difference
                            ),
                            time_difference_seconds=(
                                time_difference
                            ),
                            reference_match=(
                                reference_match
                            ),
                        ),
                    )
                )

        return candidates

    def _settlement_bank_candidates(
        self,
        settlements: list,
        banks: list,
    ) -> list[RelationshipCandidate]:

        candidates = []

        for settlement_node in settlements:

            settlement = settlement_node.record

            for bank_node in banks:

                bank = bank_node.record

                amount_difference = abs(
                    settlement.net_amount
                    - bank.credit
                )

                time_difference = abs(
                    (
                        bank.event_timestamp
                        - settlement.event_timestamp
                    ).total_seconds()
                )

                utr_match = (
                    self._normalize(
                        getattr(
                            settlement,
                            "utr",
                            None,
                        )
                    )
                    == self._normalize(
                        getattr(
                            bank,
                            "utr",
                            None,
                        )
                    )
                    and getattr(
                        settlement,
                        "utr",
                        None,
                    )
                    is not None
                )

                candidates.append(
                    RelationshipCandidate(
                        source_record_id=(
                            settlement_node.evidence_id
                        ),
                        target_record_id=(
                            bank_node.evidence_id
                        ),
                        relationship_type=(
                            "BANK_FOR_SETTLEMENT"
                        ),
                        features=CandidateFeatures(
                            amount_difference=(
                                amount_difference
                            ),
                            time_difference_seconds=(
                                time_difference
                            ),
                            utr_match=utr_match,
                        ),
                    )
                )

        return candidates

    @staticmethod
    def _normalize(
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