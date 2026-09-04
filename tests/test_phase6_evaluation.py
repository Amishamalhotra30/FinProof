from decimal import Decimal

from app.corruption.models import CorruptionType
from app.investigation.models import (
    HypothesisFinding,
    HypothesisStatus,
    HypothesisType,
    InvestigationResult,
    InvestigationStatus,
)
from scripts.run_phase6_evaluation import (
    Phase6Evaluation,
    _expected_hypotheses_for_case,
    _has_supported_expected_hypothesis,
    _is_false_explanation,
)


# ============================================================
# Evaluation metric helpers
# ============================================================


def make_evaluation(**overrides):

    values = {
        "total_cases": 100,
        "corrupted_cases": 30,
        "investigated_cases": 30,
        "fully_explained_cases": 10,
        "partially_explained_cases": 5,
        "unresolved_cases": 10,
        "insufficient_evidence_cases": 5,
        "contradiction_cases": 0,
        "validated_cases": 30,
        "hypothesis_aligned_cases": 20,
        "false_explanation_cases": 2,
        "total_explained_amount": Decimal(
            "50000.00"
        ),
        "total_discrepancy_amount": Decimal(
            "100000.00"
        ),
        "total_remaining_amount": Decimal(
            "50000.00"
        ),
        "supporting_evidence_count": 25,
        "processing_time_ms": Decimal(
            "1000.00"
        ),
    }

    values.update(overrides)

    return Phase6Evaluation(
        **values
    )


# ============================================================
# Rates
# ============================================================


def test_investigation_coverage():

    evaluation = make_evaluation(
        corrupted_cases=20,
        investigated_cases=15,
    )

    assert (
        evaluation.investigation_coverage
        == 0.75
    )


def test_investigation_coverage_is_one_when_no_corruption():

    evaluation = make_evaluation(
        corrupted_cases=0,
        investigated_cases=0,
    )

    assert (
        evaluation.investigation_coverage
        == 1.0
    )


def test_full_explanation_rate():

    evaluation = make_evaluation(
        investigated_cases=20,
        fully_explained_cases=5,
    )

    assert (
        evaluation.full_explanation_rate
        == 0.25
    )


def test_partial_explanation_rate():

    evaluation = make_evaluation(
        investigated_cases=20,
        partially_explained_cases=4,
    )

    assert (
        evaluation.partial_explanation_rate
        == 0.20
    )


def test_unresolved_rate():

    evaluation = make_evaluation(
        investigated_cases=20,
        unresolved_cases=6,
    )

    assert (
        evaluation.unresolved_rate
        == 0.30
    )


def test_contradiction_rate():

    evaluation = make_evaluation(
        investigated_cases=20,
        contradiction_cases=4,
    )

    assert (
        evaluation.contradiction_rate
        == 0.20
    )


def test_validation_rate():

    evaluation = make_evaluation(
        investigated_cases=20,
        validated_cases=18,
    )

    assert (
        evaluation.validation_rate
        == 0.90
    )


def test_hypothesis_alignment_rate():

    evaluation = make_evaluation(
        investigated_cases=20,
        hypothesis_aligned_cases=16,
    )

    assert (
        evaluation.hypothesis_alignment_rate
        == 0.80
    )


def test_false_explanation_rate():

    evaluation = make_evaluation(
        investigated_cases=20,
        false_explanation_cases=2,
    )

    assert (
        evaluation.false_explanation_rate
        == 0.10
    )


# ============================================================
# Financial explanation
# ============================================================


def test_explanation_coverage():

    evaluation = make_evaluation(
        total_explained_amount=Decimal(
            "2500.00"
        ),
        total_discrepancy_amount=Decimal(
            "5000.00"
        ),
    )

    assert (
        evaluation.explanation_coverage
        == 0.5
    )


def test_zero_discrepancy_has_full_explanation_coverage():

    evaluation = make_evaluation(
        total_explained_amount=Decimal(
            "0"
        ),
        total_discrepancy_amount=Decimal(
            "0"
        ),
    )

    assert (
        evaluation.explanation_coverage
        == 1.0
    )


# ============================================================
# Throughput
# ============================================================


def test_throughput():

    evaluation = make_evaluation(
        investigated_cases=100,
        processing_time_ms=Decimal(
            "1000"
        ),
    )

    assert (
        evaluation.throughput
        == 100.0
    )


def test_zero_processing_time_has_zero_throughput():

    evaluation = make_evaluation(
        investigated_cases=100,
        processing_time_ms=Decimal(
            "0"
        ),
    )

    assert (
        evaluation.throughput
        == 0.0
    )


# ============================================================
# Corruption → hypothesis mapping
# ============================================================


def test_missing_record_maps_to_missing_event():

    events = [
        type(
            "Event",
            (),
            {
                "case_id": "CASE_001",
                "corruption_type": (
                    CorruptionType.MISSING_RECORD
                ),
            },
        )()
    ]

    expected = (
        _expected_hypotheses_for_case(
            "CASE_001",
            events,
        )
    )

    assert expected == {
        HypothesisType.MISSING_EVENT,
    }


def test_duplicate_record_maps_to_duplicate_event():

    events = [
        type(
            "Event",
            (),
            {
                "case_id": "CASE_001",
                "corruption_type": (
                    CorruptionType.DUPLICATE_RECORD
                ),
            },
        )()
    ]

    expected = (
        _expected_hypotheses_for_case(
            "CASE_001",
            events,
        )
    )

    assert expected == {
        HypothesisType.DUPLICATE_EVENT,
    }


def test_timing_anomaly_maps_to_timing_difference():

    events = [
        type(
            "Event",
            (),
            {
                "case_id": "CASE_001",
                "corruption_type": (
                    CorruptionType.TIMING_ANOMALY
                ),
            },
        )()
    ]

    expected = (
        _expected_hypotheses_for_case(
            "CASE_001",
            events,
        )
    )

    assert expected == {
        HypothesisType.TIMING_DIFFERENCE,
    }


def test_multiple_corruptions_combine_hypotheses():

    events = [
        type(
            "Event",
            (),
            {
                "case_id": "CASE_001",
                "corruption_type": (
                    CorruptionType.DUPLICATE_RECORD
                ),
            },
        )(),
        type(
            "Event",
            (),
            {
                "case_id": "CASE_001",
                "corruption_type": (
                    CorruptionType.TIMING_ANOMALY
                ),
            },
        )(),
    ]

    expected = (
        _expected_hypotheses_for_case(
            "CASE_001",
            events,
        )
    )

    assert expected == {
        HypothesisType.DUPLICATE_EVENT,
        HypothesisType.TIMING_DIFFERENCE,
    }


# ============================================================
# Hypothesis alignment
# ============================================================


def test_supported_expected_hypothesis_is_aligned():

    result = InvestigationResult(
        investigation_id="INV_1",
        case_id="CASE_001",
        discrepancy_id="DISC_1",
        status=InvestigationStatus.RESOLVED,
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=(
                    HypothesisType.DUPLICATE_EVENT
                ),
                status=HypothesisStatus.SUPPORTED,
                explained_amount=Decimal(
                    "5000.00"
                ),
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        explained_amount=Decimal(
            "5000.00"
        ),
        remaining_unexplained=Decimal(
            "0"
        ),
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
        validated=True,
    )

    assert _has_supported_expected_hypothesis(
        result,
        {
            HypothesisType.DUPLICATE_EVENT,
        },
    )


def test_weakly_supported_expected_hypothesis_is_aligned():

    result = InvestigationResult(
        investigation_id="INV_1",
        case_id="CASE_001",
        discrepancy_id="DISC_1",
        status=InvestigationStatus.UNRESOLVED,
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=(
                    HypothesisType.TIMING_DIFFERENCE
                ),
                status=(
                    HypothesisStatus.WEAKLY_SUPPORTED
                ),
                explained_amount=Decimal(
                    "1000.00"
                ),
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        explained_amount=Decimal(
            "1000.00"
        ),
        remaining_unexplained=Decimal(
            "4000.00"
        ),
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    assert _has_supported_expected_hypothesis(
        result,
        {
            HypothesisType.TIMING_DIFFERENCE,
        },
    )


def test_unrelated_supported_hypothesis_is_not_aligned():

    result = InvestigationResult(
        investigation_id="INV_1",
        case_id="CASE_001",
        discrepancy_id="DISC_1",
        status=InvestigationStatus.RESOLVED,
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=(
                    HypothesisType.REFUND
                ),
                status=HypothesisStatus.SUPPORTED,
                explained_amount=Decimal(
                    "5000.00"
                ),
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        explained_amount=Decimal(
            "5000.00"
        ),
        remaining_unexplained=Decimal(
            "0"
        ),
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    assert not _has_supported_expected_hypothesis(
        result,
        {
            HypothesisType.DUPLICATE_EVENT,
        },
    )


# ============================================================
# False explanation detection
# ============================================================


def test_zero_explanation_is_not_false_explanation():

    result = InvestigationResult(
        investigation_id="INV_1",
        case_id="CASE_001",
        discrepancy_id="DISC_1",
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        hypotheses=[],
        explained_amount=Decimal("0"),
        remaining_unexplained=Decimal(
            "5000.00"
        ),
        supporting_evidence_ids=[],
    )

    assert not _is_false_explanation(
        result,
        {
            HypothesisType.MISSING_EVENT,
        },
    )


def test_expected_explanation_is_not_false():

    result = InvestigationResult(
        investigation_id="INV_1",
        case_id="CASE_001",
        discrepancy_id="DISC_1",
        status=InvestigationStatus.RESOLVED,
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=(
                    HypothesisType.DUPLICATE_EVENT
                ),
                status=HypothesisStatus.SUPPORTED,
                explained_amount=Decimal(
                    "5000.00"
                ),
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        explained_amount=Decimal(
            "5000.00"
        ),
        remaining_unexplained=Decimal(
            "0"
        ),
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    assert not _is_false_explanation(
        result,
        {
            HypothesisType.DUPLICATE_EVENT,
        },
    )


def test_unrelated_explanation_is_false():

    result = InvestigationResult(
        investigation_id="INV_1",
        case_id="CASE_001",
        discrepancy_id="DISC_1",
        status=InvestigationStatus.RESOLVED,
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=HypothesisType.REFUND,
                status=HypothesisStatus.SUPPORTED,
                explained_amount=Decimal(
                    "5000.00"
                ),
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        explained_amount=Decimal(
            "5000.00"
        ),
        remaining_unexplained=Decimal(
            "0"
        ),
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    assert _is_false_explanation(
        result,
        {
            HypothesisType.DUPLICATE_EVENT,
        },
    )