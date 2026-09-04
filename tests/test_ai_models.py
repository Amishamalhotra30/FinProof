from app.reconciliation.ai_models import (
    AIRelationshipProposal,
    AIProposalRelationship,
    ReviewDecision,
)


def make_proposal():

    return AIRelationshipProposal(
        source_record_id="BANK_184",
        candidate_record_id="SET_082",
        relationship=(
            AIProposalRelationship
            .LIKELY_SAME_EVENT
        ),
        supporting_evidence=(
            "same amount",
            "same settlement-day window",
            "matching merchant reference",
        ),
        contradicting_evidence=(
            "UTR not present",
        ),
        requires_review=True,
    )


def test_ai_proposal_contains_record_ids():

    proposal = make_proposal()

    assert proposal.source_record_id == "BANK_184"
    assert proposal.candidate_record_id == "SET_082"


def test_ai_proposal_contains_relationship():

    proposal = make_proposal()

    assert (
        proposal.relationship
        == AIProposalRelationship.LIKELY_SAME_EVENT
    )


def test_supporting_evidence_is_preserved():

    proposal = make_proposal()

    assert proposal.supporting_evidence == (
        "same amount",
        "same settlement-day window",
        "matching merchant reference",
    )

    assert proposal.has_supporting_evidence


def test_contradicting_evidence_is_preserved():

    proposal = make_proposal()

    assert proposal.contradicting_evidence == (
        "UTR not present",
    )

    assert proposal.has_contradicting_evidence


def test_review_escalation_is_explicit():

    proposal = make_proposal()

    assert proposal.requires_review is True
    assert proposal.decision == ReviewDecision.REVIEW


def test_evidence_count():

    proposal = make_proposal()

    assert proposal.evidence_count == 4


def test_model_metadata_is_optional():

    proposal = make_proposal()

    assert proposal.model_name is None
    assert proposal.model_version is None


def test_model_metadata_can_be_recorded():

    proposal = AIRelationshipProposal(
        source_record_id="BANK_001",
        candidate_record_id="SET_001",
        relationship=(
            AIProposalRelationship.RELATED_EVENT
        ),
        supporting_evidence=(
            "matching merchant reference",
        ),
        contradicting_evidence=(),
        requires_review=False,
        decision=ReviewDecision.ACCEPT,
        model_name="relationship-inference",
        model_version="v1",
    )

    assert proposal.model_name == (
        "relationship-inference"
    )

    assert proposal.model_version == "v1"

    assert proposal.decision == (
        ReviewDecision.ACCEPT
    )


def test_empty_evidence_is_allowed():

    proposal = AIRelationshipProposal(
        source_record_id="BANK_001",
        candidate_record_id="SET_001",
        relationship=(
            AIProposalRelationship.RELATED_EVENT
        ),
        supporting_evidence=(),
        contradicting_evidence=(),
        requires_review=True,
    )

    assert proposal.evidence_count == 0
    assert not proposal.has_supporting_evidence
    assert not proposal.has_contradicting_evidence