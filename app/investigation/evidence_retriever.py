from app.domain.enums import EventType
from app.domain.events import FinancialEvent
from app.domain.graph import EventGraph
from app.investigation.models import (
    EvidenceRelation,
    HypothesisType,
    InvestigationCase,
    InvestigationEvidence,
)


class InvestigationEvidenceRetriever:
    """
    Deterministic Phase 6 evidence retrieval engine.

    The retriever searches the supplied EventGraph for evidence
    relevant to an investigation case and/or hypothesis.

    It does not:
        - invent evidence
        - modify the EventGraph
        - infer missing events
        - determine financial root cause
        - calculate explanations
        - assign hypothesis support merely because evidence
          was retrieved
        - use an LLM

    Retrieval and reasoning are intentionally separate.
    """

    # ============================================================
    # PUBLIC API
    # ============================================================

    def retrieve(
        self,
        case: InvestigationCase,
        graph: EventGraph,
    ) -> list[InvestigationEvidence]:
        """
        Retrieve evidence relevant to an investigation case.

        Case-level retrieval starts from the explicitly affected
        events and follows observable graph relationships.
        """

        events = self._retrieve_case_events(
            case,
            graph,
        )

        return [
            self._to_evidence(
                event,
                self._classify_relationship(
                    case,
                    event,
                ),
            )
            for event in events
        ]

    def retrieve_for_hypothesis(
        self,
        case: InvestigationCase,
        hypothesis,
        graph: EventGraph,
    ) -> list[InvestigationEvidence]:
        """
        Retrieve evidence relevant to one hypothesis.

        IMPORTANT:

        The graph supplied to this method is already the
        investigation search space.

        However, we must NOT simply return every event of a
        matching EventType because that would allow unrelated
        evidence into an investigation.

        Retrieval therefore follows this order:

            1. Explicitly affected events
            2. Events directly related to affected events
            3. Events connected through the same entity
            4. For broad hypotheses, the connected case evidence
               rather than the entire graph

        Retrieval does NOT prove the hypothesis.

        Therefore retrieved evidence is marked SUPPORTS only
        when it is explicitly associated with the Phase 5
        discrepancy. Other retrieved evidence remains
        IRRELEVANT until a later reasoning component evaluates it.
        """

        allowed_types = self._allowed_event_types(
            hypothesis.hypothesis_type
        )

        candidate_events = self._connected_case_events(
            case,
            graph,
        )

        selected: dict[str, FinancialEvent] = {}

        for event in candidate_events:

            if (
                allowed_types
                and event.event_type not in allowed_types
            ):
                continue

            selected[event.event_id] = event

        # --------------------------------------------------------
        # Explicitly affected events always remain eligible.
        #
        # This prevents a narrow hypothesis from accidentally
        # dropping the exact evidence responsible for the
        # discrepancy.
        # --------------------------------------------------------

        for event_id in case.affected_event_ids:

            event = graph.events.get(event_id)

            if event is None:
                continue

            if (
                not allowed_types
                or event.event_type in allowed_types
            ):
                selected[event.event_id] = event

        ordered_events = sorted(
            selected.values(),
            key=lambda event: (
                event.timestamp,
                event.event_id,
            ),
        )

        retrieved_evidence = [
            self._to_evidence(
                event,
                self._classify_hypothesis_relationship(
                    case,
                    event,
                    hypothesis.hypothesis_type,
                ),
            )
            for event in ordered_events
        ]

        # --------------------------------------------------------
        # TEMPORARY PHASE 6 DIAGNOSTIC
        # --------------------------------------------------------
        # This does not change retrieval or classification.
        # It exposes the exact relationship/amount carried from
        # EventGraph -> InvestigationEvidence for the affected
        # events that are allowed to support a hypothesis.
        supporting_debug = [
            (
                item.evidence_id,
                item.relationship.value,
                item.amount,
                item.source,
                item.record_id,
            )
            for item in retrieved_evidence
            if (
                item.relationship == EvidenceRelation.SUPPORTS
                and item.evidence_id in case.affected_event_ids
            )
        ]

        if supporting_debug:
            print()
            print("---------- PHASE 6 EVIDENCE DEBUG ----------")
            print(f"CASE       : {case.case_id}")
            print(f"CONTROL    : {case.control_failure}")
            print(f"HYPOTHESIS : {hypothesis.hypothesis_type.value}")
            print(f"DIFFERENCE : {case.difference}")
            print(f"AFFECTED   : {case.affected_event_ids}")
            print("SUPPORTING EVIDENCE:")
            for (
                evidence_id,
                relationship,
                amount,
                source,
                record_id,
            ) in supporting_debug:
                print(
                    f"  {evidence_id} | "
                    f"REL={relationship} | "
                    f"AMOUNT={amount} | "
                    f"SOURCE={source} | "
                    f"RECORD={record_id}"
                )
            print("---------------------------------------------")

        return retrieved_evidence

    # ============================================================
    # CASE RETRIEVAL
    # ============================================================

    def _retrieve_case_events(
        self,
        case: InvestigationCase,
        graph: EventGraph,
    ) -> list[FinancialEvent]:
        """
        Retrieve events connected to the Phase 5 discrepancy.

        No global graph scan is performed.

        This is important because the EventGraph may contain
        unrelated financial activity.
        """

        return self._connected_case_events(
            case,
            graph,
        )

    def _connected_case_events(
        self,
        case: InvestigationCase,
        graph: EventGraph,
    ) -> list[FinancialEvent]:
        """
        Return the observable event neighborhood around the
        affected Phase 5 events.

        The traversal is deliberately bounded.

        Starting points:
            - Phase 5 affected event IDs

        Traversal:
            - related_event_ids
            - same entity_id

        The traversal does not use arbitrary case-ID substring
        matching as a substitute for graph relationships.
        """

        selected: dict[str, FinancialEvent] = {}

        # --------------------------------------------------------
        # 1. Start from explicit Phase 5 affected events.
        # --------------------------------------------------------

        queue: list[str] = []

        for event_id in case.affected_event_ids:

            if event_id in graph.events:
                queue.append(event_id)

        # --------------------------------------------------------
        # 2. Traverse observable relationships.
        # --------------------------------------------------------

        visited: set[str] = set()

        while queue:

            event_id = queue.pop(0)

            if event_id in visited:
                continue

            visited.add(event_id)

            event = graph.events.get(event_id)

            if event is None:
                continue

            selected[event.event_id] = event

            # ----------------------------------------------------
            # Explicit graph relationships.
            # ----------------------------------------------------

            for related_id in event.related_event_ids:

                if related_id in graph.events:
                    if related_id not in visited:
                        queue.append(related_id)

            # ----------------------------------------------------
            # Same financial entity.
            #
            # This captures payment → refund/fee/settlement/
            # bank evidence even when the edge is not explicitly
            # represented in related_event_ids.
            # ----------------------------------------------------

            for candidate in graph.events.values():

                if candidate.event_id in visited:
                    continue

                if candidate.entity_id == event.entity_id:
                    queue.append(
                        candidate.event_id
                    )

        # --------------------------------------------------------
        # 3. If no explicit affected event is available, use the
        #    case's case-ID relationship as a conservative
        #    fallback.
        #
        # This supports benchmark-generated cases without making
        # case-ID matching the primary retrieval mechanism.
        # --------------------------------------------------------

        if not selected:

            for event in graph.events.values():

                if self._belongs_to_case(
                    event,
                    case,
                ):
                    selected[event.event_id] = event

        # --------------------------------------------------------
        # 4. Stable deterministic ordering.
        # --------------------------------------------------------

        return sorted(
            selected.values(),
            key=lambda event: (
                event.timestamp,
                event.event_id,
            ),
        )

    # ============================================================
    # HYPOTHESIS → EVENT TYPE MAPPING
    # ============================================================

    @staticmethod
    def _allowed_event_types(
        hypothesis_type: HypothesisType,
    ) -> set[EventType]:
        """
        Map each bounded Phase 6 hypothesis to the domain event
        types that can provide evidence for it.

        This is retrieval scope, not a conclusion.
        """

        mapping = {

            HypothesisType.REFUND: {
                EventType.REFUND_CREATED,
            },

            HypothesisType.FEE: {
                EventType.FEE_APPLIED,
            },

            HypothesisType.TAX: {
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
            },

            HypothesisType.ADJUSTMENT: {
                EventType.ADJUSTMENT_APPLIED,
            },

            HypothesisType.PARTIAL_SETTLEMENT: {
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
                EventType.BANK_CREDIT,
            },

            HypothesisType.BUNDLED_SETTLEMENT: {
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
                EventType.BANK_CREDIT,
            },

            HypothesisType.DUPLICATE_EVENT: {
                EventType.ORDER_CREATED,
                EventType.PAYMENT_CAPTURED,
                EventType.REFUND_CREATED,
                EventType.FEE_APPLIED,
                EventType.ADJUSTMENT_APPLIED,
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
                EventType.BANK_CREDIT,
            },

            HypothesisType.TIMING_DIFFERENCE: {
                EventType.PAYMENT_CAPTURED,
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
                EventType.BANK_CREDIT,
            },

            HypothesisType.MISSING_EVENT: {
                EventType.ORDER_CREATED,
                EventType.PAYMENT_CAPTURED,
                EventType.REFUND_CREATED,
                EventType.FEE_APPLIED,
                EventType.ADJUSTMENT_APPLIED,
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
                EventType.BANK_CREDIT,
            },

            HypothesisType.SOURCE_DATA_ERROR: {
                EventType.ORDER_CREATED,
                EventType.PAYMENT_CAPTURED,
                EventType.REFUND_CREATED,
                EventType.FEE_APPLIED,
                EventType.ADJUSTMENT_APPLIED,
                EventType.SETTLEMENT_CREATED,
                EventType.SETTLEMENT_PROCESSED,
                EventType.BANK_CREDIT,
            },

            HypothesisType.UNDETERMINED: set(),
        }

        return mapping.get(
            hypothesis_type,
            set(),
        )

    # ============================================================
    # CONTROL → HYPOTHESIS MAPPING
    # ============================================================

    @staticmethod
    def _hypothesis_types(
        case: InvestigationCase,
    ) -> set[HypothesisType]:
        """
        Map a Phase 5 control failure to the bounded Phase 6
        hypothesis vocabulary.

        This determines candidate retrieval categories only.
        It does not determine the root cause.
        """

        mapping = {

            "REFUND_AMOUNT": {
                HypothesisType.REFUND,
            },

            "REFUND_PAYMENT_COMPLETENESS": {
                HypothesisType.REFUND,
                HypothesisType.MISSING_EVENT,
            },

            "FEE_AMOUNT": {
                HypothesisType.FEE,
            },

            "ADJUSTMENT_AMOUNT": {
                HypothesisType.ADJUSTMENT,
            },

            "SETTLEMENT_AMOUNT": {
                HypothesisType.PARTIAL_SETTLEMENT,
                HypothesisType.BUNDLED_SETTLEMENT,
                HypothesisType.REFUND,
                HypothesisType.FEE,
                HypothesisType.ADJUSTMENT,
            },

            "BANK_CREDIT_AMOUNT": {
                HypothesisType.PARTIAL_SETTLEMENT,
                 HypothesisType.BUNDLED_SETTLEMENT,
                HypothesisType.TIMING_DIFFERENCE,
                HypothesisType.SOURCE_DATA_ERROR,
            },

            "SETTLEMENT_BANK_COMPLETENESS": {
                HypothesisType.PARTIAL_SETTLEMENT,
                HypothesisType.BUNDLED_SETTLEMENT,
                HypothesisType.MISSING_EVENT,
                HypothesisType.TIMING_DIFFERENCE,
            },

            "PAYMENT_SETTLEMENT_COMPLETENESS": {
                HypothesisType.MISSING_EVENT,
                HypothesisType.PARTIAL_SETTLEMENT,
                HypothesisType.TIMING_DIFFERENCE,
            },

            "DUPLICATE_EVENT": {
                HypothesisType.DUPLICATE_EVENT,
            },

            "EVENT_ORDERING": {
                HypothesisType.TIMING_DIFFERENCE,
            },

            "SETTLEMENT_TIMING": {
                HypothesisType.TIMING_DIFFERENCE,
            },

            "CURRENCY_CONSISTENCY": {
                HypothesisType.SOURCE_DATA_ERROR,
            },
        }

        return mapping.get(
            case.control_failure,
            {
                HypothesisType.UNDETERMINED,
            },
        )

    # ============================================================
    # CASE MEMBERSHIP
    # ============================================================

    @staticmethod
    def _belongs_to_case(
        event: FinancialEvent,
        case: InvestigationCase,
    ) -> bool:
        """
        Conservative benchmark-compatible case membership check.

        This is only a fallback.

        Normal retrieval is relationship-based.
        """

        case_id = case.case_id

        if not case_id:
            return False

        if case_id in event.event_id:
            return True

        if case_id in event.entity_id:
            return True

        if event.event_id in case.affected_event_ids:
            return True

        if event.entity_id in case.affected_event_ids:
            return True

        return False

    # ============================================================
    # RELATIONSHIP CLASSIFICATION
    # ============================================================

    @staticmethod
    def _classify_relationship(
        case: InvestigationCase,
        event: FinancialEvent,
    ) -> EvidenceRelation:
        """
        Case-level retrieval classification.

        An explicitly affected event is supporting evidence
        from the perspective of the Phase 5 discrepancy.

        Other retrieved events are merely relevant candidates.
        """

        if event.event_id in case.affected_event_ids:
            return EvidenceRelation.SUPPORTS

        return EvidenceRelation.IRRELEVANT

    @staticmethod
    def _classify_hypothesis_relationship(
        case: InvestigationCase,
        event: FinancialEvent,
        hypothesis_type: HypothesisType | None = None,
    ) -> EvidenceRelation:
        """
        Classify evidence for a specific hypothesis.

        Retrieval alone must not turn an affected event into proof
        of every possible hypothesis.

        In particular, a BANK_CREDIT_AMOUNT discrepancy identifies
        the bank entry as evidence of the observed bank amount, but
        the bank entry by itself does not prove a partial or bundled
        settlement. For that control, the affected bank event is
        supporting evidence only for SOURCE_DATA_ERROR.

        Other hypotheses retain the existing benchmark-compatible
        behavior: an explicitly affected event is evidence associated
        with the discrepancy, while non-affected events remain
        IRRELEVANT until hypothesis evaluation.
        """

        if event.event_id not in case.affected_event_ids:
            return EvidenceRelation.IRRELEVANT

        if case.control_failure == "BANK_CREDIT_AMOUNT":
            if hypothesis_type == HypothesisType.SOURCE_DATA_ERROR:
                return EvidenceRelation.SUPPORTS

            return EvidenceRelation.IRRELEVANT

        return EvidenceRelation.SUPPORTS

    # ============================================================
    # EVENT → INVESTIGATION EVIDENCE
    # ============================================================

    @staticmethod
    def _to_evidence(
        event: FinancialEvent,
        relationship: EvidenceRelation,
    ) -> InvestigationEvidence:
        """
        Convert a domain FinancialEvent into an immutable
        investigation evidence representation.

        No financial interpretation is introduced here.
        """

        return InvestigationEvidence(
            evidence_id=event.event_id,
            source=event.source.value,
            record_id=event.entity_id,
            amount=event.amount,
            timestamp=event.timestamp.isoformat(),
            relationship=relationship,
            description=(
                f"{event.event_type.value} "
                f"for entity {event.entity_id}"
            ),
            metadata=dict(event.metadata),
        )


# ================================================================
# PUBLIC CONVENIENCE FUNCTIONS
# ================================================================

def retrieve_investigation_evidence(
    case: InvestigationCase,
    graph: EventGraph,
) -> list[InvestigationEvidence]:
    """
    Convenience function for case-level retrieval.
    """

    return InvestigationEvidenceRetriever().retrieve(
        case,
        graph,
    )


def retrieve_evidence(
    case: InvestigationCase,
    graph: EventGraph,
) -> list[InvestigationEvidence]:
    """
    Public compatibility alias for case-level retrieval.
    """

    return InvestigationEvidenceRetriever().retrieve(
        case,
        graph,
    )


# ================================================================
# BACKWARD COMPATIBILITY
# ================================================================

EvidenceRetriever = InvestigationEvidenceRetriever