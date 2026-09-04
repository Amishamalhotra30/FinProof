from decimal import Decimal

from app.reconciliation.candidate_generator import (
    CandidateFeatures,
    RelationshipCandidate,
)
from app.reconciliation.scorer import (
    CandidateScorer,
)


def candidate(
    amount_difference=Decimal("0"),
    time_difference_seconds=300,
    reference_match=False,
    utr_match=False,
):

    return RelationshipCandidate(
        source_record_id="PAY_001",
        target_record_id="SET_001",
        relationship_type="SETTLEMENT_FOR_PAYMENT",
        features=CandidateFeatures(
            amount_difference=amount_difference,
            time_difference_seconds=time_difference_seconds,
            reference_match=reference_match,
            utr_match=utr_match,
        ),
    )


def test_exact_utr_is_strongest_signal():

    result = CandidateScorer().score(
        candidate(
            utr_match=True,
        )
    )

    assert result.score >= Decimal("0.70")

    assert (
        "Exact UTR match"
        in result.reasons
    )


def test_reference_match_adds_confidence():

    result_without_reference = (
        CandidateScorer().score(
            candidate()
        )
    )

    result_with_reference = (
        CandidateScorer().score(
            candidate(
                reference_match=True
            )
        )
    )

    assert (
        result_with_reference.score
        > result_without_reference.score
    )

    assert (
        "Reference matches"
        in result_with_reference.reasons
    )


def test_exact_amount_adds_supporting_evidence():

    result = CandidateScorer().score(
        candidate(
            amount_difference=Decimal("0")
        )
    )

    assert (
        result.score
        >= Decimal("0.10")
    )


def test_close_amount_scores_higher_than_large_difference():

    close = CandidateScorer().score(
        candidate(
            amount_difference=Decimal("10")
        )
    )

    far = CandidateScorer().score(
        candidate(
            amount_difference=Decimal("5000")
        )
    )

    assert close.score > far.score


def test_close_timestamp_scores_higher():

    close = CandidateScorer().score(
        candidate(
            time_difference_seconds=60
        )
    )

    far = CandidateScorer().score(
        candidate(
            time_difference_seconds=90000
        )
    )

    assert close.score > far.score


def test_combined_evidence_increases_confidence():

    weak = CandidateScorer().score(
        candidate()
    )

    strong = CandidateScorer().score(
        candidate(
            amount_difference=Decimal("0"),
            time_difference_seconds=60,
            reference_match=True,
            utr_match=True,
        )
    )

    assert strong.score > weak.score

    assert strong.confidence == strong.score


def test_score_is_never_above_one():

    result = CandidateScorer().score(
        candidate(
            amount_difference=Decimal("0"),
            time_difference_seconds=60,
            reference_match=True,
            utr_match=True,
        )
    )

    assert result.score <= Decimal("1")


def test_scoring_is_explainable():

    result = CandidateScorer().score(
        candidate(
            amount_difference=Decimal("10"),
            time_difference_seconds=300,
            reference_match=True,
            utr_match=True,
        )
    )

    assert len(result.reasons) >= 3

    assert all(
        isinstance(reason, str)
        for reason in result.reasons
    )


def test_missing_features_do_not_crash():

    candidate_without_features = (
        RelationshipCandidate(
            source_record_id="PAY_001",
            target_record_id="SET_001",
            relationship_type=(
                "SETTLEMENT_FOR_PAYMENT"
            ),
            features=CandidateFeatures(),
        )
    )

    result = CandidateScorer().score(
        candidate_without_features
    )

    assert result.score == Decimal("0")
    assert result.confidence == Decimal("0")