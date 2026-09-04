from collections.abc import Iterable

from app.domain.enums import EventType
from app.ingestion.canonical_models import (
    CanonicalAdjustment,
    CanonicalBankEntry,
    CanonicalFee,
    CanonicalOrder,
    CanonicalPayment,
    CanonicalRefund,
    CanonicalSettlement,
)
from app.reconstruction.models import (
    ReconstructedEvent,
    TimestampType,
)


class EventBuilder:
    """
    Converts observed Phase 2 canonical records into Phase 4
    reconstructed events.

    This class only translates observed evidence.

    It does not:
        - infer missing events
        - repair records
        - determine financial correctness
        - compare against ground truth
        - investigate discrepancies
    """

    def build_order(
        self,
        record: CanonicalOrder,
    ) -> ReconstructedEvent:

        return ReconstructedEvent(
            event_id=record.evidence_id,
            event_type=EventType.ORDER_CREATED,
            timestamp=record.event_timestamp,
            timestamp_type=TimestampType.CREATED_AT,
            amount=record.amount,
            currency=record.currency,
            source_evidence_ids=[record.evidence_id],
            attributes={
                "record_type": "order",
                "order_id": record.order_id,
                "customer_id": record.customer_id,
                "status": record.status,
            },
        )

    def build_payment(
        self,
        record: CanonicalPayment,
    ) -> ReconstructedEvent:

        return ReconstructedEvent(
            event_id=record.evidence_id,
            event_type=EventType.PAYMENT_CAPTURED,
            timestamp=record.event_timestamp,
            timestamp_type=TimestampType.CAPTURED_AT,
            amount=record.amount,
            currency=record.currency,
            source_evidence_ids=[record.evidence_id],
            attributes={
                "record_type": "payment",
                "payment_id": record.payment_id,
                "order_id": record.order_id,
                "status": record.status,
            },
        )

    def build_refund(
        self,
        record: CanonicalRefund,
    ) -> ReconstructedEvent:

        return ReconstructedEvent(
            event_id=record.evidence_id,
            event_type=EventType.REFUND_CREATED,
            timestamp=record.event_timestamp,
            timestamp_type=TimestampType.EVENT_TIME,
            amount=record.amount,
            currency="INR",
            source_evidence_ids=[record.evidence_id],
            attributes={
                "record_type": "refund",
                "refund_id": record.refund_id,
                "payment_id": record.payment_id,
                "status": record.status,
            },
        )

    def build_fee(
        self,
        record: CanonicalFee,
    ) -> ReconstructedEvent:

        return ReconstructedEvent(
            event_id=record.evidence_id,
            event_type=EventType.FEE_APPLIED,
            timestamp=record.event_timestamp,
            timestamp_type=TimestampType.EVENT_TIME,
            amount=record.amount,
            currency="INR",
            source_evidence_ids=[record.evidence_id],
            attributes={
                "record_type": "fee",
                "fee_id": record.fee_id,
                "payment_id": record.payment_id,
                "status": record.status,
            },
        )

    def build_adjustment(
        self,
        record: CanonicalAdjustment,
    ) -> ReconstructedEvent:

        event_type = self._adjustment_event_type(
            record.event_type
        )

        return ReconstructedEvent(
            event_id=record.evidence_id,
            event_type=event_type,
            timestamp=record.event_timestamp,
            timestamp_type=TimestampType.EVENT_TIME,
            amount=record.amount,
            currency="INR",
            source_evidence_ids=[record.evidence_id],
            attributes={
                "record_type": "adjustment",
                "event_id": record.event_id,
                "payment_id": record.payment_id,
                "status": record.status,
                "source_event_type": record.event_type,
            },
        )

    def build_settlement(
        self,
        record: CanonicalSettlement,
    ) -> ReconstructedEvent:

        return ReconstructedEvent(
            event_id=record.evidence_id,
            event_type=self._settlement_event_type(
                record.status
            ),
            timestamp=record.event_timestamp,
            timestamp_type=TimestampType.PROCESSED_AT,
            amount=record.net_amount,
            currency="INR",
            source_evidence_ids=[record.evidence_id],
            attributes={
                "record_type": "settlement",
                "settlement_id": record.settlement_id,
                "payment_id": (
                    record.payment_id
                    if record.payment_id is not None
                    else ""
                ),
                "reference": record.reference,
                "gross_amount": str(
                    record.gross_amount
                ),
                "fee": str(record.fee),
                "tax": str(record.tax),
                "adjustment": str(record.adjustment),
                "net_amount": str(record.net_amount),
                "status": record.status,
                "utr": record.utr or "",
            },
        )

    def build_bank(
        self,
        record: CanonicalBankEntry,
    ) -> ReconstructedEvent:

        return ReconstructedEvent(
            event_id=record.evidence_id,
            event_type=EventType.BANK_CREDIT,
            timestamp=record.event_timestamp,
            timestamp_type=TimestampType.VALUE_DATE,
            amount=record.credit,
            currency=record.currency,
            source_evidence_ids=[record.evidence_id],
            attributes={
                "record_type": "bank",
                "transaction_id": record.transaction_id,
                "narration": record.narration,
                "normalized_narration": (
                    record.normalized_narration
                ),
                "debit": str(record.debit),
                "utr": record.utr or "",
            },
        )

    def build(
        self,
        records: Iterable[object],
    ) -> list[ReconstructedEvent]:
        """
        Build reconstructed events from a collection of canonical
        records.

        Unsupported objects are ignored rather than fabricated.
        """

        events: list[ReconstructedEvent] = []

        builders = (
            (CanonicalOrder, self.build_order),
            (CanonicalPayment, self.build_payment),
            (CanonicalRefund, self.build_refund),
            (CanonicalFee, self.build_fee),
            (CanonicalAdjustment, self.build_adjustment),
            (CanonicalSettlement, self.build_settlement),
            (CanonicalBankEntry, self.build_bank),
        )

        for record in records:
            for record_type, builder in builders:
                if isinstance(record, record_type):
                    events.append(builder(record))
                    break

        return events

    @staticmethod
    def _settlement_event_type(
        status: str,
    ) -> EventType:

        normalized = status.strip().upper()

        if normalized in {
            "CREATED",
            "CREATE",
            "PENDING",
        }:
            return EventType.SETTLEMENT_CREATED

        return EventType.SETTLEMENT_PROCESSED

    @staticmethod
    def _adjustment_event_type(
        event_type: str,
    ) -> EventType:

        normalized = event_type.strip().upper()

        if normalized == EventType.ADJUSTMENT_APPLIED.value:
            return EventType.ADJUSTMENT_APPLIED

        return EventType.ADJUSTMENT_APPLIED