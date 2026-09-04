from dataclasses import dataclass
from enum import Enum


class AIProposalRelationship(str, Enum):
    LIKELY_SAME_EVENT = "LIKELY_SAME_EVENT"
    RELATED_EVENT = "RELATED_EVENT"


class ReviewDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class AIRelationshipProposal:
    """
    Structured proposal produced by AI-assisted reconciliation.

    This is a proposal only. It is not a confirmed financial
    relationship and must not modify canonical evidence.
    """

    source_record_id: str
    candidate_record_id: str

    relationship: AIProposalRelationship

    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]

    requires_review: bool

    decision: ReviewDecision = ReviewDecision.REVIEW

    model_name: str | None = None
    model_version: str | None = None

    @property
    def has_supporting_evidence(self) -> bool:
        return bool(self.supporting_evidence)

    @property
    def has_contradicting_evidence(self) -> bool:
        return bool(self.contradicting_evidence)

    @property
    def evidence_count(self) -> int:
        return (
            len(self.supporting_evidence)
            + len(self.contradicting_evidence)
        )