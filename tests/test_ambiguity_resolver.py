from decimal import Decimal

from app.reconciliation.ambiguity_resolver import (
    AmbiguityResolver,
    ResolutionStatus,
)
from app.reconciliation.candidate_generator import (
    CandidateFeatures,
    RelationshipCandidate,
)
from app.reconciliation.scorer import (
    CandidateScorer,
)


def make_candidate(
    target_id: str,
    *,
    amount_difference="0",
    time_difference=60,
    reference_match=False,
    utr_match=False,
):
    candidate = RelationshipCandidate(
        source_record_id="PAY_001",
        target_record_id=target_id,
        relationship_type=(
            "SETTLEMENT_FOR_PAYMENT"
        ),
        features=CandidateFeatures(
            amount_difference=Decimal(
                amount_difference
            ),
            time_difference_seconds=(
                time_difference
            ),
            reference_match=(
                reference_match
            ),
            utr_match=utr_match,
        ),
    )

    return CandidateScorer().score(
        candidate
    )


def test_empty_candidates_are_unresolved():

    result = AmbiguityResolver().resolve([])

    assert (
        result.status
        == ResolutionStatus.UNRESOLVED
    )

    assert result.candidate is None

    assert result.confidence == Decimal("0")


def test_single_strong_candidate_is_confirmed():

    candidate = make_candidate(
        "SET_001",
        reference_match=True,
        utr_match=True,
    )

    result = AmbiguityResolver().resolve(
        [candidate]
    )

    assert (
        result.status
        == ResolutionStatus.CONFIRMED
    )

    assert (
        result.candidate
        == candidate
    )


def test_weak_candidate_is_unresolved():

    candidate = make_candidate(
        "SET_001",
        amount_difference="5000",
        time_difference=90000,
    )

    result = AmbiguityResolver().resolve(
        [candidate]
    )

    assert (
        result.status
        == ResolutionStatus.UNRESOLVED
    )

    assert result.candidate == candidate


def test_close_candidates_are_ambiguous():

    first = make_candidate(
        "SET_001",
        reference_match=True,
        amount_difference="0",
        time_difference=60,
    )

    second = make_candidate(
        "SET_002",
        reference_match=True,
        amount_difference="10",
        time_difference=300,
    )

    result = AmbiguityResolver().resolve(
        [first, second]
    )

    assert (
        result.status
        == ResolutionStatus.AMBIGUOUS
    )

    assert result.candidate is None


def test_clear_winner_is_confirmed():

    winner = make_candidate(
        "SET_001",
        reference_match=True,
        utr_match=True,
        amount_difference="0",
        time_difference=60,
    )

    loser = make_candidate(
        "SET_002",
        amount_difference="5000",
        time_difference=90000,
    )

    result = AmbiguityResolver().resolve(
        [loser, winner]
    )

    assert (
        result.status
        == ResolutionStatus.CONFIRMED
    )

    assert (
        result.candidate
        == winner
    )


def test_candidates_are_ranked_by_score():

    weak = make_candidate(
        "SET_WEAK",
        amount_difference="1000",
        time_difference=7200,
    )

    strong = make_candidate(
        "SET_STRONG",
        reference_match=True,
        utr_match=True,
        amount_difference="0",
        time_difference=60,
    )

    result = AmbiguityResolver().resolve(
        [weak, strong]
    )

    assert (
        result.candidate.target_record_id
        == "SET_STRONG"
    )


def test_custom_thresholds_are_respected():

    candidate = make_candidate(
        "SET_001",
        reference_match=True,
    )

    resolver = AmbiguityResolver(
        minimum_confidence=Decimal("0.95")
    )

    result = resolver.resolve(
        [candidate]
    )

    assert (
        result.status
        == ResolutionStatus.UNRESOLVED
    )


def test_margin_threshold_is_respected():

    first = make_candidate(
        "SET_001",
        reference_match=True,
        amount_difference="0",
        time_difference=60,
    )

    second = make_candidate(
        "SET_002",
        reference_match=True,
        amount_difference="10",
        time_difference=60,
    )

    resolver = AmbiguityResolver(
        minimum_margin=Decimal("0.50")
    )

    result = resolver.resolve(
        [first, second]
    )

    assert (
        result.status
        == ResolutionStatus.AMBIGUOUS
    )


def test_resolution_contains_explanation():

    candidate = make_candidate(
        "SET_001",
        reference_match=True,
        utr_match=True,
    )

    result = AmbiguityResolver().resolve(
        [candidate]
    )

    assert result.reason
    assert isinstance(
        result.reason,
        str,
    )