import pytest

from app.decisions.models import (
    CaseState,
    DecisionOutcome,
    ReviewAction,
)
from app.decisions.state_machine import (
    DecisionStateMachine,
    InvalidStateTransition,
)


def test_new_case_starts_open():
    machine = DecisionStateMachine()

    assert machine.state == CaseState.OPEN
    assert not machine.is_terminal
    assert machine.history == ()


def test_open_moves_to_verification():
    machine = DecisionStateMachine()

    transition = machine.start_verification()

    assert transition.from_state == CaseState.OPEN
    assert transition.to_state == CaseState.VERIFICATION
    assert transition.trigger == "START_VERIFICATION"
    assert machine.state == CaseState.VERIFICATION


def test_verification_can_start_investigation():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_investigation()

    assert machine.state == CaseState.INVESTIGATION


def test_verification_can_go_directly_to_decision():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()

    assert machine.state == CaseState.DECISION


def test_investigation_moves_to_decision():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_investigation()
    machine.start_decision()

    assert machine.state == CaseState.DECISION


def test_auto_resolved_is_terminal():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.AUTO_RESOLVED
    )

    assert machine.state == CaseState.AUTO_RESOLVED
    assert machine.is_terminal


def test_pending_is_terminal():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.PENDING
    )

    assert machine.state == CaseState.PENDING
    assert machine.is_terminal


def test_blocked_is_terminal():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.BLOCKED
    )

    assert machine.state == CaseState.BLOCKED
    assert machine.is_terminal


def test_resolved_with_approval_enters_human_review():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.RESOLVED_WITH_APPROVAL
    )

    assert machine.state == CaseState.HUMAN_REVIEW


def test_human_review_can_be_approved():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.HUMAN_REVIEW
    )

    machine.apply_review_action(
        ReviewAction.APPROVE
    )

    assert machine.state == CaseState.APPROVED
    assert machine.is_terminal


def test_human_review_can_be_rejected():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.HUMAN_REVIEW
    )

    machine.apply_review_action(
        ReviewAction.REJECT
    )

    assert machine.state == CaseState.REJECTED
    assert not machine.is_terminal


def test_rejected_case_can_be_reinvestigated():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.HUMAN_REVIEW
    )
    machine.apply_review_action(
        ReviewAction.REJECT
    )
    machine.reinvestigate()

    assert machine.state == CaseState.REINVESTIGATION

    machine.start_investigation()

    assert machine.state == CaseState.INVESTIGATION


def test_more_evidence_can_trigger_reinvestigation():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.HUMAN_REVIEW
    )
    machine.apply_review_action(
        ReviewAction.REQUEST_MORE_EVIDENCE
    )

    assert machine.state == (
        CaseState.REQUEST_MORE_EVIDENCE
    )

    machine.reinvestigate()

    assert machine.state == CaseState.REINVESTIGATION


def test_invalid_transition_is_rejected():
    machine = DecisionStateMachine()

    with pytest.raises(
        InvalidStateTransition
    ):
        machine.start_decision()


def test_terminal_state_cannot_transition():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.AUTO_RESOLVED
    )

    with pytest.raises(
        InvalidStateTransition
    ):
        machine.start_investigation()


def test_history_records_every_transition():
    machine = DecisionStateMachine()

    machine.start_verification()
    machine.start_decision()
    machine.apply_decision(
        DecisionOutcome.AUTO_RESOLVED
    )

    assert len(machine.history) == 3

    assert machine.history[0].from_state == (
        CaseState.OPEN
    )

    assert machine.history[0].to_state == (
        CaseState.VERIFICATION
    )

    assert machine.history[1].to_state == (
        CaseState.DECISION
    )

    assert machine.history[2].to_state == (
        CaseState.AUTO_RESOLVED
    )


def test_can_transition_does_not_mutate_state():
    machine = DecisionStateMachine()

    assert machine.can_transition(
        "START_VERIFICATION"
    )

    assert machine.state == CaseState.OPEN
    assert machine.history == ()


def test_allowed_triggers_are_explicit():
    assert DecisionStateMachine.allowed_triggers(
        CaseState.OPEN
    ) == ("START_VERIFICATION",)

    assert DecisionStateMachine.allowed_triggers(
        CaseState.DECISION
    ) == (
        "AUTO_RESOLVE",
        "PENDING",
        "HUMAN_REVIEW",
        "BLOCK",
    )


def test_terminal_states_are_exposed():
    terminal = (
        DecisionStateMachine.terminal_states()
    )

    assert CaseState.AUTO_RESOLVED in terminal
    assert CaseState.PENDING in terminal
    assert CaseState.BLOCKED in terminal
    assert CaseState.APPROVED in terminal


def test_trigger_is_case_insensitive_and_trimmed():
    machine = DecisionStateMachine()

    machine.transition(
        "  start_verification  "
    )

    assert machine.state == CaseState.VERIFICATION