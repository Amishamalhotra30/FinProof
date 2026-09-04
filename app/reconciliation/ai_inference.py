from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.reconciliation.ai_models import (
    AIRelationshipProposal,
)
from app.reconciliation.models import (
    MatchMethod,
)


class AIInferenceProvider(ABC):
    """
    Provider-independent interface for AI-assisted
    relationship inference.

    Implementations must return structured relationship
    proposals. They must never directly modify the
    reconciliation graph or canonical evidence.
    """

    @abstractmethod
    def infer(
        self,
        source_record: object,
        candidates: Sequence[object],
    ) -> list[AIRelationshipProposal]:
        """
        Produce relationship proposals for the supplied
        source record and candidate records.
        """
        raise NotImplementedError


class DeterministicAIInferenceProvider(
    AIInferenceProvider
):
    """
    Test/development provider.

    It does not call an external model. It simply converts
    explicitly supplied candidate evidence into structured
    proposals.

    This exists so the AI boundary can be tested without
    requiring network access or API credentials.
    """

    def infer(
        self,
        source_record: object,
        candidates: Sequence[object],
    ) -> list[AIRelationshipProposal]:

        source_id = self._record_id(source_record)

        proposals: list[AIRelationshipProposal] = []

        for candidate in candidates:

            target_id = self._record_id(candidate)

            if source_id is None or target_id is None:
                continue

            proposals.append(
                AIRelationshipProposal(
                    source_record_id=source_id,
                    candidate_record_id=target_id,
                    relationship=(
                        self._relationship()
                    ),
                    supporting_evidence=(
                        "candidate supplied for AI review",
                    ),
                    contradicting_evidence=(),
                    requires_review=True,
                    model_name="deterministic-test-provider",
                    model_version="v1",
                )
            )

        return proposals

    @staticmethod
    def _record_id(
        record: object,
    ) -> str | None:

        for attribute in (
            "evidence_id",
            "payment_id",
            "settlement_id",
            "transaction_id",
            "refund_id",
            "fee_id",
            "event_id",
            "order_id",
        ):
            value = getattr(
                record,
                attribute,
                None,
            )

            if value:
                return str(value)

        return None

    @staticmethod
    def _relationship():

        from app.reconciliation.ai_models import (
            AIProposalRelationship,
        )

        return (
            AIProposalRelationship
            .LIKELY_SAME_EVENT
        )


class AIInferenceEngine:
    """
    Thin orchestration layer around an AI inference provider.

    It converts provider output into the structured Phase 3
    proposal contract and does not itself confirm relationships.
    """

    def __init__(
        self,
        provider: AIInferenceProvider,
    ):
        self.provider = provider

    def infer(
        self,
        source_record: object,
        candidates: Sequence[object],
    ) -> list[AIRelationshipProposal]:

        proposals = self.provider.infer(
            source_record,
            candidates,
        )

        return [
            proposal
            for proposal in proposals
            if self._is_valid_proposal(
                proposal
            )
        ]

    @staticmethod
    def _is_valid_proposal(
        proposal: AIRelationshipProposal,
    ) -> bool:

        if not proposal.source_record_id:
            return False

        if not proposal.candidate_record_id:
            return False

        if not proposal.supporting_evidence:
            return False

        return True