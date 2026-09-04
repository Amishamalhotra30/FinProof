from dataclasses import dataclass
from enum import Enum

from app.decisions.models import (
    CaseState,
    DecisionOutcome,
    ReviewAction,
)


class InvalidStateTransition(ValueError):
    """Raised when a workflow attempts an illegal state transition."""


@dataclass(frozen=True)
class StateTransition:
    """
    Represents one explicit workflow transition.
    """

    from_state: CaseState
    to_state: CaseState
    trigger: str


class DecisionStateMachine:
    """
    Deterministic state machine for Phase 7 case workflows.

    The state machine is intentionally narrow:
        - it does not make financial decisions
        - it does not evaluate evidence
        - it does not modify financial records
        - it only enforces legal workflow transitions
    """

    _TRANSITIONS: dict[
        CaseState,
        dict[str, CaseState],
    ] = {
        CaseState.OPEN: {
            "START_VERIFICATION": CaseState.VERIFICATION,
        },
        CaseState.VERIFICATION: {
            "START_INVESTIGATION": CaseState.INVESTIGATION,
            "START_DECISION": CaseState.DECISION,
        },
        CaseState.INVESTIGATION: {
            "START_DECISION": CaseState.DECISION,
        },
        CaseState.DECISION: {
            "AUTO_RESOLVE": CaseState.AUTO_RESOLVED,
            "PENDING": CaseState.PENDING,
            "HUMAN_REVIEW": CaseState.HUMAN_REVIEW,
            "BLOCK": CaseState.BLOCKED,
        },
        CaseState.HUMAN_REVIEW: {
            "APPROVE": CaseState.APPROVED,
            "REJECT": CaseState.REJECTED,
            "REQUEST_MORE_EVIDENCE": (
                CaseState.REQUEST_MORE_EVIDENCE
            ),
        },
        CaseState.REJECTED: {
            "REINVESTIGATE": CaseState.REINVESTIGATION,
        },
        CaseState.REQUEST_MORE_EVIDENCE: {
            "REINVESTIGATE": CaseState.REINVESTIGATION,
        },
        CaseState.REINVESTIGATION: {
            "START_INVESTIGATION": CaseState.INVESTIGATION,
        },
    }

    _TERMINAL_STATES = {
        CaseState.AUTO_RESOLVED,
        CaseState.PENDING,
        CaseState.BLOCKED,
        CaseState.APPROVED,
    }

    def __init__(
        self,
        initial_state: CaseState = CaseState.OPEN,
    ):
        self._state = initial_state
        self._history: list[StateTransition] = []

    @property
    def state(self) -> CaseState:
        """Return the current workflow state."""

        return self._state

    @property
    def history(self) -> tuple[StateTransition, ...]:
        """Return immutable transition history."""

        return tuple(self._history)

    @property
    def is_terminal(self) -> bool:
        """Whether the current state is terminal."""

        return self._state in self._TERMINAL_STATES

    def can_transition(
        self,
        trigger: str,
    ) -> bool:
        """
        Check whether a transition is legal without mutating state.
        """

        return trigger in self._TRANSITIONS.get(
            self._state,
            {},
        )

    def transition(
        self,
        trigger: str,
    ) -> StateTransition:
        """
        Perform one legal state transition.

        Raises:
            InvalidStateTransition:
                If the requested transition is not legal.
        """

        trigger = trigger.strip().upper()

        next_state = self._TRANSITIONS.get(
            self._state,
            {},
        ).get(trigger)

        if next_state is None:
            raise InvalidStateTransition(
                f"Invalid transition: "
                f"{self._state.value} "
                f"--[{trigger}]--> ?"
            )

        transition = StateTransition(
            from_state=self._state,
            to_state=next_state,
            trigger=trigger,
        )

        self._state = next_state
        self._history.append(transition)

        return transition

    def reset(
        self,
        state: CaseState = CaseState.OPEN,
    ) -> None:
        """
        Reset the state machine.

        Intended for constructing a fresh workflow instance,
        not for bypassing workflow controls in production.
        """

        self._state = state
        self._history.clear()

    # ========================================================
    # Convenience transitions
    # ========================================================

    def start_verification(self) -> StateTransition:
        return self.transition(
            "START_VERIFICATION"
        )

    def start_investigation(self) -> StateTransition:
        return self.transition(
            "START_INVESTIGATION"
        )

    def start_decision(self) -> StateTransition:
        return self.transition(
            "START_DECISION"
        )

    def apply_decision(
        self,
        outcome: DecisionOutcome,
    ) -> StateTransition:
        """
        Convert a policy decision into a workflow transition.
        """

        mapping = {
            DecisionOutcome.AUTO_RESOLVED: "AUTO_RESOLVE",
            DecisionOutcome.PENDING: "PENDING",
            DecisionOutcome.HUMAN_REVIEW: "HUMAN_REVIEW",
            DecisionOutcome.BLOCKED: "BLOCK",
            DecisionOutcome.RESOLVED_WITH_APPROVAL: (
                "HUMAN_REVIEW"
            ),
        }

        try:
            trigger = mapping[outcome]
        except KeyError as exc:
            raise InvalidStateTransition(
                f"Unsupported decision outcome: {outcome}"
            ) from exc

        return self.transition(trigger)

    def apply_review_action(
        self,
        action: ReviewAction,
    ) -> StateTransition:
        """
        Convert a human review action into a workflow transition.
        """

        mapping = {
            ReviewAction.APPROVE: "APPROVE",
            ReviewAction.REJECT: "REJECT",
            ReviewAction.REQUEST_MORE_EVIDENCE: (
                "REQUEST_MORE_EVIDENCE"
            ),
        }

        try:
            trigger = mapping[action]
        except KeyError as exc:
            raise InvalidStateTransition(
                f"Unsupported review action: {action}"
            ) from exc

        return self.transition(trigger)

    def reinvestigate(self) -> StateTransition:
        """
        Move a rejected/evidence-requested case back into
        investigation.
        """

        if self._state not in {
            CaseState.REJECTED,
            CaseState.REQUEST_MORE_EVIDENCE,
        }:
            raise InvalidStateTransition(
                "Reinvestigation is only allowed after "
                "REJECTED or REQUEST_MORE_EVIDENCE."
            )

        transition = self.transition(
            "REINVESTIGATE"
        )

        return transition

    @classmethod
    def allowed_triggers(
        cls,
        state: CaseState,
    ) -> tuple[str, ...]:
        """
        Return all legal triggers for a state.
        """

        return tuple(
            cls._TRANSITIONS.get(
                state,
                {},
            ).keys()
        )

    @classmethod
    def terminal_states(
        cls,
    ) -> frozenset[CaseState]:
        """Return the terminal workflow states."""

        return frozenset(cls._TERMINAL_STATES)