from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.reconciliation.ai_models import (
    AIRelationshipProposal,
    AIProposalRelationship,
    ReviewDecision,
)


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ReviewItem:
    """
    Explicit review record for an AI-assisted relationship.

    A ReviewItem is not a confirmed relationship.
    It preserves the AI proposal and its supporting and
    contradicting evidence for later human or policy review.
    """

    review_id: str

    source_record_id: str
    candidate_record_id: str

    relationship: AIProposalRelationship

    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]

    status: ReviewStatus

    created_at: datetime

    model_name: str | None = None
    model_version: str | None = None

    @property
    def requires_review(self) -> bool:
        return self.status == ReviewStatus.PENDING

    @property
    def evidence_count(self) -> int:
        return (
            len(self.supporting_evidence)
            + len(self.contradicting_evidence)
        )


class ReviewEscalator:
    """
    Converts AI relationship proposals into explicit review items.

    It never confirms or modifies a reconciliation relationship.
    """

    def escalate(
        self,
        proposal: AIRelationshipProposal,
    ) -> ReviewItem:

        status = (
            ReviewStatus.PENDING
            if proposal.requires_review
            else self._status_from_decision(
                proposal.decision
            )
        )

        return ReviewItem(
            review_id=self._review_id(
                proposal
            ),
            source_record_id=(
                proposal.source_record_id
            ),
            candidate_record_id=(
                proposal.candidate_record_id
            ),
            relationship=proposal.relationship,
            supporting_evidence=(
                proposal.supporting_evidence
            ),
            contradicting_evidence=(
                proposal.contradicting_evidence
            ),
            status=status,
            created_at=datetime.now(),
            model_name=proposal.model_name,
            model_version=proposal.model_version,
        )

    @staticmethod
    def escalate_many(
        proposals: list[AIRelationshipProposal],
    ) -> list[ReviewItem]:

        escalator = ReviewEscalator()

        return [
            escalator.escalate(proposal)
            for proposal in proposals
        ]

    @staticmethod
    def _status_from_decision(
        decision: ReviewDecision,
    ) -> ReviewStatus:

        if decision == ReviewDecision.ACCEPT:
            return ReviewStatus.ACCEPTED

        if decision == ReviewDecision.REJECT:
            return ReviewStatus.REJECTED

        return ReviewStatus.PENDING

    @staticmethod
    def _review_id(
        proposal: AIRelationshipProposal,
    ) -> str:

        return (
            "REVIEW_"
            f"{proposal.source_record_id}_"
            f"{proposal.candidate_record_id}"
        )