from dataclasses import dataclass
from decimal import Decimal

from app.reconciliation.candidate_generator import (
    RelationshipCandidate,
)


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: RelationshipCandidate
    score: Decimal
    confidence: Decimal
    reasons: list[str]

    @property
    def source_record_id(self) -> str:
        return self.candidate.source_record_id

    @property
    def target_record_id(self) -> str:
        return self.candidate.target_record_id

    @property
    def relationship_type(self) -> str:
        return self.candidate.relationship_type


class CandidateScorer:
    """
    Deterministic scoring of relationship candidates.

    This layer does NOT confirm relationships.
    It converts candidate features into an explainable
    confidence score that later resolution logic can use.
    """

    def score(
        self,
        candidate: RelationshipCandidate,
    ) -> ScoredCandidate:

        features = candidate.features

        score = Decimal("0")
        reasons: list[str] = []

        if features.utr_match:
            score += Decimal("0.70")
            reasons.append(
                "Exact UTR match"
            )

        if features.reference_match:
            score += Decimal("0.20")
            reasons.append(
                "Reference matches"
            )

        amount_score = self._amount_score(
            features.amount_difference
        )

        score += amount_score

        if amount_score > Decimal("0"):
            reasons.append(
                f"Amount difference "
                f"{features.amount_difference}"
            )

        time_score = self._time_score(
            features.time_difference_seconds
        )

        score += time_score

        if time_score > Decimal("0"):
            reasons.append(
                "Timestamp proximity"
            )

        if score > Decimal("1"):
            score = Decimal("1")

        return ScoredCandidate(
            candidate=candidate,
            score=score,
            confidence=score,
            reasons=reasons,
        )

    @staticmethod
    def _amount_score(
        difference: Decimal | None,
    ) -> Decimal:

        if difference is None:
            return Decimal("0")

        difference = abs(difference)

        if difference == Decimal("0"):
            return Decimal("0.10")

        if difference <= Decimal("10"):
            return Decimal("0.08")

        if difference <= Decimal("100"):
            return Decimal("0.06")

        if difference <= Decimal("500"):
            return Decimal("0.04")

        if difference <= Decimal("1000"):
            return Decimal("0.02")

        return Decimal("0")

    @staticmethod
    def _time_score(
        seconds: float | None,
    ) -> Decimal:

        if seconds is None:
            return Decimal("0")

        seconds = abs(seconds)

        if seconds <= 300:
            return Decimal("0.10")

        if seconds <= 1800:
            return Decimal("0.08")

        if seconds <= 3600:
            return Decimal("0.06")

        if seconds <= 7200:
            return Decimal("0.04")

        if seconds <= 86400:
            return Decimal("0.02")

        return Decimal("0")