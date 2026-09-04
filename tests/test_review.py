from app.reconciliation.ai_models import (
    AIRelationshipProposal,
    AIProposalRelationship,
    ReviewDecision,
)
from app.reconciliation.review import (
    ReviewEscalator,
    ReviewStatus,
)


def make_proposal(
    *,
    requires_review=True,
    decision=ReviewDecision.REVIEW,
):

    return AIRelationshipProposal(
        source_record_id="BANK_001",
        candidate_record_id="SET_001",
        relationship=(
            AIProposalRelationship
            .LIKELY_SAME_EVENT
        ),
        supporting_evidence=(
            "same amount",
            "matching merchant reference",
        ),
        contradicting_evidence=(
            "UTR not present",
        ),
        requires_review=requires_review,
        decision=decision,
        model_name="test-model",
        model_version="v1",
    )


def test_proposal_becomes_pending_review():

    item = ReviewEscalator().escalate(
        make_proposal()
    )

    assert item.status == ReviewStatus.PENDING
    assert item.requires_review is True


def test_review_item_preserves_record_ids():

    item = ReviewEscalator().escalate(
        make_proposal()
    )

    assert item.source_record_id == "BANK_001"
    assert item.candidate_record_id == "SET_001"


def test_review_item_preserves_relationship():

    item = ReviewEscalator().escalate(
        make_proposal()
    )

    assert item.relationship == (
        AIProposalRelationship
        .LIKELY_SAME_EVENT
    )


def test_supporting_evidence_is_preserved():

    item = ReviewEscalator().escalate(
        make_proposal()
    )

    assert item.supporting_evidence == (
        "same amount",
        "matching merchant reference",
    )


def test_contradicting_evidence_is_preserved():

    item = ReviewEscalator().escalate(
        make_proposal()
    )

    assert item.contradicting_evidence == (
        "UTR not present",
    )


def test_evidence_count():

    item = ReviewEscalator().escalate(
        make_proposal()
    )

    assert item.evidence_count == 3


def test_model_provenance_is_preserved():

    item = ReviewEscalator().escalate(
        make_proposal()
    )

    assert item.model_name == "test-model"
    assert item.model_version == "v1"


def test_review_id_is_deterministic():

    first = ReviewEscalator().escalate(
        make_proposal()
    )

    second = ReviewEscalator().escalate(
        make_proposal()
    )

    assert first.review_id == second.review_id

    assert first.review_id == (
        "REVIEW_BANK_001_SET_001"
    )


def test_accept_decision_becomes_accepted():

    proposal = make_proposal(
        requires_review=False,
        decision=ReviewDecision.ACCEPT,
    )

    item = ReviewEscalator().escalate(
        proposal
    )

    assert item.status == ReviewStatus.ACCEPTED
    assert item.requires_review is False


def test_reject_decision_becomes_rejected():

    proposal = make_proposal(
        requires_review=False,
        decision=ReviewDecision.REJECT,
    )

    item = ReviewEscalator().escalate(
        proposal
    )

    assert item.status == ReviewStatus.REJECTED
    assert item.requires_review is False


def test_review_decision_remains_pending():

    proposal = make_proposal(
        requires_review=False,
        decision=ReviewDecision.REVIEW,
    )

    item = ReviewEscalator().escalate(
        proposal
    )

    assert item.status == ReviewStatus.PENDING
    assert item.requires_review is True


def test_multiple_proposals_are_escalated():

    proposals = [
        make_proposal(),
        AIRelationshipProposal(
            source_record_id="BANK_002",
            candidate_record_id="SET_002",
            relationship=(
                AIProposalRelationship
                .RELATED_EVENT
            ),
            supporting_evidence=(
                "same merchant",
            ),
            contradicting_evidence=(),
            requires_review=True,
        ),
    ]

    items = ReviewEscalator.escalate_many(
        proposals
    )

    assert len(items) == 2

    assert {
        item.review_id
        for item in items
    } == {
        "REVIEW_BANK_001_SET_001",
        "REVIEW_BANK_002_SET_002",
    }


def test_escalation_does_not_modify_proposal():

    proposal = make_proposal()

    before = proposal

    ReviewEscalator().escalate(
        proposal
    )

    assert proposal == before