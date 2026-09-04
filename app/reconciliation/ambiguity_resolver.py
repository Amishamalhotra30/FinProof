from dataclasses import dataclass
from decimal import Decimal

from app.reconciliation.scorer import (
    ScoredCandidate,
)


class ResolutionStatus:
    CONFIRMED = "CONFIRMED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class Resolution:
    status: str
    candidate: ScoredCandidate | None
    confidence: Decimal
    reason: str


class AmbiguityResolver:
    """
    Deterministic decision layer for scored candidates.

    A candidate is confirmed only when:

        1. Its score reaches the minimum confidence threshold.
        2. It has a sufficiently large margin over the
           next-best candidate.

    Multiple plausible candidates that are too close are
    marked AMBIGUOUS instead of being arbitrarily selected.
    """

    def __init__(
        self,
        minimum_confidence: Decimal = Decimal("0.70"),
        minimum_margin: Decimal = Decimal("0.15"),
    ):
        self.minimum_confidence = (
            minimum_confidence
        )

        self.minimum_margin = (
            minimum_margin
        )

    def resolve(
        self,
        candidates: list[ScoredCandidate],
    ) -> Resolution:

        if not candidates:
            return Resolution(
                status=ResolutionStatus.UNRESOLVED,
                candidate=None,
                confidence=Decimal("0"),
                reason="No candidates available",
            )

        ranked = sorted(
            candidates,
            key=lambda candidate: candidate.score,
            reverse=True,
        )

        best = ranked[0]

        # -------------------------------------------------
        # Multiple candidates:
        # First determine whether the competition itself
        # is ambiguous.
        # -------------------------------------------------

        if len(ranked) > 1:

            second = ranked[1]

            margin = (
                best.score
                - second.score
            )

            if (
                best.score
                >= self.minimum_confidence
                and margin
                < self.minimum_margin
            ):
                return Resolution(
                    status=ResolutionStatus.AMBIGUOUS,
                    candidate=None,
                    confidence=best.confidence,
                    reason=(
                        "Top candidates are too close "
                        "to resolve deterministically"
                    ),
                )

            # If both candidates represent meaningful
            # competing evidence, but the winner itself
            # does not clear the confidence threshold,
            # we still classify the case as ambiguous
            # rather than pretending there is simply no
            # candidate.
            if (
                best.score > Decimal("0")
                and second.score > Decimal("0")
                and margin < self.minimum_margin
            ):
                return Resolution(
                    status=ResolutionStatus.AMBIGUOUS,
                    candidate=None,
                    confidence=best.confidence,
                    reason=(
                        "Multiple candidates have "
                        "competing evidence"
                    ),
                )

        # -------------------------------------------------
        # Confidence threshold
        # -------------------------------------------------

        if (
            best.score
            < self.minimum_confidence
        ):
            return Resolution(
                status=ResolutionStatus.UNRESOLVED,
                candidate=best,
                confidence=best.confidence,
                reason=(
                    "Best candidate does not meet "
                    "minimum confidence threshold"
                ),
            )

        # -------------------------------------------------
        # Single strong candidate
        # -------------------------------------------------

        if len(ranked) == 1:
            return Resolution(
                status=ResolutionStatus.CONFIRMED,
                candidate=best,
                confidence=best.confidence,
                reason=(
                    "Single candidate meets "
                    "minimum confidence threshold"
                ),
            )

        # -------------------------------------------------
        # Multiple candidates with a clear winner
        # -------------------------------------------------

        second = ranked[1]

        margin = (
            best.score
            - second.score
        )

        if margin < self.minimum_margin:
            return Resolution(
                status=ResolutionStatus.AMBIGUOUS,
                candidate=None,
                confidence=best.confidence,
                reason=(
                    "Top candidates are too close "
                    "to resolve deterministically"
                ),
            )

        return Resolution(
            status=ResolutionStatus.CONFIRMED,
            candidate=best,
            confidence=best.confidence,
            reason=(
                "Best candidate exceeds the "
                "minimum confidence and margin"
            ),
        )