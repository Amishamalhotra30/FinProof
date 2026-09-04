from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.decisions.service import (
    DecisionService,
    DecisionServiceResult,
)
from app.investigation.models import InvestigationResult
from app.verification.models import VerificationResult


@dataclass(frozen=True)
class BatchDecisionRunResult:
    """
    Application-level result for Phase 7 decisions.
    """

    batch_id: str
    decisions: tuple[DecisionServiceResult, ...]


class DecisionRuntime:
    """
    Application adapter around the existing Phase 7 decision engine.

    This class does not implement policy. It only connects the
    verification/investigation outputs produced by the runtime
    pipeline to DecisionService.
    """

    def __init__(
        self,
        service: DecisionService | None = None,
    ) -> None:
        self.service = (
            service
            or DecisionService()
        )

    def decide(
        self,
        *,
        batch_id: str,
        verification: VerificationResult,
        investigations: tuple[
            InvestigationResult, ...
        ],
    ) -> BatchDecisionRunResult:
        """
        Produce one Phase 7 decision for each investigation case.

        Verification and investigation objects are existing Phase 5
        and Phase 6 runtime outputs. No benchmark information is
        accepted.
        """

        investigation_by_case = {
            investigation.case_id: investigation
            for investigation in investigations
        }

        decisions: list[
            DecisionServiceResult
        ] = []

        # A verification result identifies the case it represents.
        # The investigation workflow may produce zero or more cases.
        #
        # Prefer investigation cases when available because Phase 7
        # operates at the case level.
        for investigation in investigations:
            decision = self.service.decide(
                verification=verification,
                investigation=investigation,
            )

            decisions.append(
                decision
            )

        # If there are no investigation cases, still allow Phase 7
        # to make a verification-only decision.
        if not decisions:
            decision = self.service.decide(
                verification=verification,
                investigation=None,
            )

            decisions.append(
                decision
            )

        return BatchDecisionRunResult(
            batch_id=batch_id,
            decisions=tuple(decisions),
        )


def decide_batch(
    *,
    batch_id: str,
    verification: VerificationResult,
    investigations: tuple[
        InvestigationResult, ...
    ],
) -> BatchDecisionRunResult:
    """
    Convenience application entry point.
    """

    return DecisionRuntime().decide(
        batch_id=batch_id,
        verification=verification,
        investigations=investigations,
    )