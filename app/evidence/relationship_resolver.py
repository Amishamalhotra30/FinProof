from app.evidence.graph import EvidenceGraph
from app.ingestion.coordinator import (
    MultiSourceIngestionResult,
)


class RelationshipResolver:

    def resolve(
        self,
        result: MultiSourceIngestionResult,
    ) -> EvidenceGraph:

        graph = EvidenceGraph()

        self._add_nodes(
            graph,
            result,
        )

        self._link_payment_relationships(
            graph,
            result,
        )

        self._link_settlement_bank(
            graph,
            result,
        )

        return graph

    def _add_nodes(
        self,
        graph: EvidenceGraph,
        result: MultiSourceIngestionResult,
    ) -> None:

        sources = (
            ("order", result.orders.valid_records),
            ("payment", result.payments.valid_records),
            ("refund", result.refunds.valid_records),
            ("fee", result.fees.valid_records),
            (
                "adjustment",
                result.adjustments.valid_records,
            ),
            (
                "settlement",
                result.settlements.valid_records,
            ),
            ("bank", result.bank.valid_records),
        )

        for record_type, records in sources:

            for record in records:

                graph.add_node(
                    evidence_id=record.evidence_id,
                    record_type=record_type,
                    record=record,
                )

    def _link_payment_relationships(
        self,
        graph: EvidenceGraph,
        result: MultiSourceIngestionResult,
    ) -> None:

        payments = result.payments.valid_records

        payment_nodes = {
            payment.payment_id: payment
            for payment in payments
        }

        for refund in result.refunds.valid_records:

            payment = payment_nodes.get(
                refund.payment_id
            )

            if payment is not None:

                graph.add_edge(
                    source_id=payment.evidence_id,
                    target_id=refund.evidence_id,
                    relationship="refunded_by",
                )

        for fee in result.fees.valid_records:

            payment = payment_nodes.get(
                fee.payment_id
            )

            if payment is not None:

                graph.add_edge(
                    source_id=payment.evidence_id,
                    target_id=fee.evidence_id,
                    relationship="charged_fee",
                )

        for adjustment in (
            result.adjustments.valid_records
        ):

            payment = payment_nodes.get(
                adjustment.payment_id
            )

            if payment is not None:

                graph.add_edge(
                    source_id=payment.evidence_id,
                    target_id=adjustment.evidence_id,
                    relationship="adjusted_by",
                )

        for settlement in (
            result.settlements.valid_records
        ):

            if settlement.payment_id is None:
                continue

            payment = payment_nodes.get(
                settlement.payment_id
            )

            if payment is not None:

                graph.add_edge(
                    source_id=payment.evidence_id,
                    target_id=settlement.evidence_id,
                    relationship="settled_by",
                )

    def _link_settlement_bank(
        self,
        graph: EvidenceGraph,
        result: MultiSourceIngestionResult,
    ) -> None:

        bank_by_utr = {}

        for bank in result.bank.valid_records:

            if bank.utr is not None:

                bank_by_utr[bank.utr] = bank

        for settlement in (
            result.settlements.valid_records
        ):

            if settlement.utr is None:
                continue

            bank = bank_by_utr.get(
                settlement.utr
            )

            if bank is not None:

                graph.add_edge(
                    source_id=settlement.evidence_id,
                    target_id=bank.evidence_id,
                    relationship="credited_to",
                )