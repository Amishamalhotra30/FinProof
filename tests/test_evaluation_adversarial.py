from decimal import Decimal

from app.evaluation.adversarial import (
    ContradictoryEvidenceRetriever,
    DuplicateEvidenceRetriever,
    EmptyEvidenceRetriever,
    FailingEvidenceRetriever,
    MalformedEvidenceRetriever,
    run_adversarial_case,
    run_standard_adversarial_suite,
)
from app.investigation.models import (
    InvestigationStatus,
)


def test_empty_retrieval_is_safe():
    result = run_adversarial_case(
        "EMPTY_RETRIEVAL",
        EmptyEvidenceRetriever(),
    )

    assert result.safe
    assert (
        result.status
        == InvestigationStatus.INSUFFICIENT_EVIDENCE
    )
    assert result.explained_amount == Decimal("0")


def test_retrieval_failure_does_not_fabricate():
    result = run_adversarial_case(
        "RETRIEVAL_FAILURE",
        FailingEvidenceRetriever(),
    )

    assert result.safe
    assert result.error_type == (
        "RetrievalFailure"
    )
    assert result.explained_amount == Decimal("0")


def test_malformed_evidence_cannot_explain_money():
    result = run_adversarial_case(
        "MALFORMED_EVIDENCE",
        MalformedEvidenceRetriever(),
    )

    assert result.safe
    assert result.explained_amount == Decimal("0")


def test_duplicate_evidence_counted_once():
    result = run_adversarial_case(
        "DUPLICATE_EVIDENCE",
        DuplicateEvidenceRetriever(),
    )

    assert result.safe
    assert result.explained_amount == Decimal("500")
    assert (
        result.explained_amount
        != Decimal("1500")
    )


def test_contradictory_evidence_is_safe():
    result = run_adversarial_case(
        "CONTRADICTORY_EVIDENCE",
        ContradictoryEvidenceRetriever(),
    )

    assert result.safe
    assert (
        result.status
        == InvestigationStatus.CONTRADICTION
    )
    assert result.explained_amount == Decimal("0")


def test_standard_adversarial_suite():
    results = run_standard_adversarial_suite()

    assert len(results) == 5

    assert all(
        result.safe
        for result in results
    )


def test_no_adversarial_case_produces_negative_explanation():
    results = run_standard_adversarial_suite()

    assert all(
        result.explained_amount
        >= Decimal("0")
        for result in results
    )