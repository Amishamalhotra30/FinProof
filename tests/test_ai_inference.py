from dataclasses import dataclass

from app.reconciliation.ai_inference import (
    AIInferenceEngine,
    AIInferenceProvider,
    DeterministicAIInferenceProvider,
)
from app.reconciliation.ai_models import (
    AIProposalRelationship,
)


@dataclass
class Record:

    evidence_id: str


def test_deterministic_provider_returns_proposal():

    source = Record("BANK_001")
    candidate = Record("SET_001")

    provider = (
        DeterministicAIInferenceProvider()
    )

    proposals = provider.infer(
        source,
        [candidate],
    )

    assert len(proposals) == 1

    proposal = proposals[0]

    assert proposal.source_record_id == (
        "BANK_001"
    )

    assert proposal.candidate_record_id == (
        "SET_001"
    )

    assert proposal.relationship == (
        AIProposalRelationship
        .LIKELY_SAME_EVENT
    )


def test_provider_marks_proposal_for_review():

    source = Record("BANK_001")
    candidate = Record("SET_001")

    proposal = (
        DeterministicAIInferenceProvider()
        .infer(
            source,
            [candidate],
        )[0]
    )

    assert proposal.requires_review is True


def test_provider_records_model_metadata():

    source = Record("BANK_001")
    candidate = Record("SET_001")

    proposal = (
        DeterministicAIInferenceProvider()
        .infer(
            source,
            [candidate],
        )[0]
    )

    assert proposal.model_name == (
        "deterministic-test-provider"
    )

    assert proposal.model_version == "v1"


def test_multiple_candidates_produce_multiple_proposals():

    source = Record("BANK_001")

    candidates = [
        Record("SET_001"),
        Record("SET_002"),
        Record("SET_003"),
    ]

    proposals = (
        DeterministicAIInferenceProvider()
        .infer(
            source,
            candidates,
        )
    )

    assert len(proposals) == 3

    assert {
        proposal.candidate_record_id
        for proposal in proposals
    } == {
        "SET_001",
        "SET_002",
        "SET_003",
    }


def test_empty_candidates_produce_no_proposals():

    source = Record("BANK_001")

    proposals = (
        DeterministicAIInferenceProvider()
        .infer(
            source,
            [],
        )
    )

    assert proposals == []


def test_engine_delegates_to_provider():

    class StubProvider(
        AIInferenceProvider
    ):

        def __init__(self):
            self.called = False

        def infer(
            self,
            source_record,
            candidates,
        ):

            self.called = True

            return (
                DeterministicAIInferenceProvider()
                .infer(
                    source_record,
                    candidates,
                )
            )

    provider = StubProvider()

    engine = AIInferenceEngine(
        provider
    )

    proposals = engine.infer(
        Record("BANK_001"),
        [Record("SET_001")],
    )

    assert provider.called is True
    assert len(proposals) == 1


def test_engine_rejects_proposal_without_supporting_evidence():

    class InvalidProvider(
        AIInferenceProvider
    ):

        def infer(
            self,
            source_record,
            candidates,
        ):

            from app.reconciliation.ai_models import (
                AIRelationshipProposal,
                AIProposalRelationship,
            )

            return [
                AIRelationshipProposal(
                    source_record_id="BANK_001",
                    candidate_record_id="SET_001",
                    relationship=(
                        AIProposalRelationship
                        .LIKELY_SAME_EVENT
                    ),
                    supporting_evidence=(),
                    contradicting_evidence=(),
                    requires_review=True,
                )
            ]

    engine = AIInferenceEngine(
        InvalidProvider()
    )

    result = engine.infer(
        Record("BANK_001"),
        [Record("SET_001")],
    )

    assert result == []


def test_engine_rejects_proposal_without_source_id():

    class InvalidProvider(
        AIInferenceProvider
    ):

        def infer(
            self,
            source_record,
            candidates,
        ):

            from app.reconciliation.ai_models import (
                AIRelationshipProposal,
                AIProposalRelationship,
            )

            return [
                AIRelationshipProposal(
                    source_record_id="",
                    candidate_record_id="SET_001",
                    relationship=(
                        AIProposalRelationship
                        .LIKELY_SAME_EVENT
                    ),
                    supporting_evidence=(
                        "same amount",
                    ),
                    contradicting_evidence=(),
                    requires_review=True,
                )
            ]

    result = AIInferenceEngine(
        InvalidProvider()
    ).infer(
        Record("BANK_001"),
        [Record("SET_001")],
    )

    assert result == []


def test_engine_rejects_proposal_without_candidate_id():

    class InvalidProvider(
        AIInferenceProvider
    ):

        def infer(
            self,
            source_record,
            candidates,
        ):

            from app.reconciliation.ai_models import (
                AIRelationshipProposal,
                AIProposalRelationship,
            )

            return [
                AIRelationshipProposal(
                    source_record_id="BANK_001",
                    candidate_record_id="",
                    relationship=(
                        AIProposalRelationship
                        .LIKELY_SAME_EVENT
                    ),
                    supporting_evidence=(
                        "same amount",
                    ),
                    contradicting_evidence=(),
                    requires_review=True,
                )
            ]

    result = AIInferenceEngine(
        InvalidProvider()
    ).infer(
        Record("BANK_001"),
        [Record("SET_001")],
    )

    assert result == []