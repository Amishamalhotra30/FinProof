from app.domain.events import FinancialEvent
from app.domain.enums import EventType, RecordSource
from app.domain.graph import EventGraph
from app.ingestion.canonical_models import (
    CanonicalAdjustment,
    CanonicalBankEntry,
    CanonicalFee,
    CanonicalOrder,
    CanonicalPayment,
    CanonicalRefund,
    CanonicalSettlement,
)
from app.reconciliation.graph import ReconciliationGraph
from app.reconciliation.models import RelationshipType
from app.reconstruction.event_builder import EventBuilder
from app.reconstruction.models import (
    ReconstructedEvent,
)


class EventGraphBuilder:
    """
    Builds the Phase 4 event graph from the Phase 3
    reconciliation graph.

    Phase 3 relationships are treated as observed evidence.
    They are not re-matched or reinterpreted here.

    This class does not:
        - infer missing events
        - repair records
        - determine financial correctness
        - access ground truth
        - investigate discrepancies
    """

    def __init__(
        self,
        event_builder: EventBuilder | None = None,
    ):
        self.event_builder = (
            event_builder
            or EventBuilder()
        )

    def build(
        self,
        reconciliation_graph: ReconciliationGraph,
    ) -> EventGraph:
        """
        Convert every supported canonical node into a domain
        FinancialEvent and then project confirmed/candidate
        reconciliation relationships into event relationships.
        """

        event_graph = EventGraph()

        event_map: dict[
            str,
            ReconstructedEvent,
        ] = {}

        # -------------------------------------------------
        # Step 1:
        # Convert canonical records into reconstructed events.
        # -------------------------------------------------

        for record_id, record in (
            reconciliation_graph.nodes.items()
        ):
            reconstructed = self._build_event(
                record
            )

            if reconstructed is None:
                continue

            event = self._to_financial_event(
                reconstructed
            )

            event_graph.add_event(event)

            event_map[
                record_id
            ] = reconstructed

        # -------------------------------------------------
        # Step 2:
        # Project Phase 3 relationships into the event graph.
        # -------------------------------------------------

        for relationship in (
            reconciliation_graph.relationships
        ):
            source_event = event_map.get(
                relationship.source_record_id
            )

            target_event = event_map.get(
                relationship.target_record_id
            )

            if (
                source_event is None
                or target_event is None
            ):
                continue

            self._apply_relationship(
                event_graph=event_graph,
                source_event_id=source_event.event_id,
                target_event_id=target_event.event_id,
                relationship_type=(
                    relationship.relationship_type
                ),
            )

            # Relationship provenance is retained
            # on both reconstructed events.
            source_event.relationship_ids.append(
                relationship.relationship_id
            )

            target_event.relationship_ids.append(
                relationship.relationship_id
            )

        return event_graph

    def build_reconstructed_events(
        self,
        reconciliation_graph: ReconciliationGraph,
    ) -> list[ReconstructedEvent]:
        """
        Build reconstructed events without projecting relationships.

        This is useful for callers that need the event representation
        before graph construction.
        """

        events: list[ReconstructedEvent] = []

        for record in (
            reconciliation_graph.nodes.values()
        ):
            event = self._build_event(record)

            if event is not None:
                events.append(event)

        return events

    def _build_event(
        self,
        record: object,
    ) -> ReconstructedEvent | None:
        """
        Convert one supported canonical record into a
        ReconstructedEvent.
        """

        events = self.event_builder.build(
            [record]
        )

        if not events:
            return None

        return events[0]

    @staticmethod
    def _to_financial_event(
        event: ReconstructedEvent,
    ) -> FinancialEvent:

        source = EventGraphBuilder._source_from_attributes(
            event.attributes
        )

        entity_id = (
            EventGraphBuilder._entity_id_from_attributes(
                event.attributes,
                event.event_id,
            )
        )

        return FinancialEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            entity_id=entity_id,
            amount=event.amount,
            currency=event.currency,
            timestamp=event.timestamp,
            related_event_ids=[],
            source=source,
            metadata={
                **event.attributes,
                "timestamp_type": (
                    event.timestamp_type.value
                ),
                "source_evidence_ids": ",".join(
                    event.source_evidence_ids
                ),
            },
        )
    @staticmethod
    def _apply_relationship(
        event_graph: EventGraph,
        source_event_id: str,
        target_event_id: str,
        relationship_type: RelationshipType,
    ) -> None:
        """
        Project a Phase 3 relationship into the directed
        Phase 4 event graph.

        The Phase 3 relationship direction is preserved.
        """

        if (
            relationship_type
            in {
                RelationshipType.ORDER_FOR_PAYMENT,
                RelationshipType.PAYMENT_FOR_ORDER,
                RelationshipType.REFUND_FOR_PAYMENT,
                RelationshipType.FEE_FOR_PAYMENT,
                RelationshipType.ADJUSTMENT_FOR_PAYMENT,
                RelationshipType.SETTLEMENT_FOR_PAYMENT,
                RelationshipType.BANK_FOR_SETTLEMENT,
                RelationshipType.BANK_FOR_SETTLEMENT_GROUP,
            }
        ):
            event_graph.add_relationship(
                source_event_id,
                target_event_id,
            )

    @staticmethod
    def _source_from_attributes(
        attributes: dict[str, str],
    ) -> RecordSource:
        record_type = attributes.get(
            "record_type",
            "",
        ).upper()

        mapping = {
            "ORDER": RecordSource.ORDER,
            "PAYMENT": RecordSource.PAYMENT,
            "REFUND": RecordSource.REFUND,
            "FEE": RecordSource.FEE,
            "ADJUSTMENT": RecordSource.ADJUSTMENT,
            "SETTLEMENT": RecordSource.SETTLEMENT,
            "BANK": RecordSource.BANK,
        }

        return mapping.get(
            record_type,
            RecordSource.PAYMENT,
        )

    @staticmethod
    def _entity_id_from_attributes(
        attributes: dict[str, str],
        fallback: str,
    ) -> str:
        """
        Prefer the domain entity identifier appropriate to
        the record type.
        """

        for key in (
            "payment_id",
            "order_id",
            "refund_id",
            "fee_id",
            "event_id",
            "settlement_id",
            "transaction_id",
        ):
            value = attributes.get(key)

            if value:
                return value

        return fallback