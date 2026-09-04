from decimal import Decimal

import pytest

from app.investigation.models import (
    HypothesisFinding,
    HypothesisStatus,
    HypothesisType,
    InvestigationCase,
    InvestigationResult,
    InvestigationStatus,
)
from app.investigation.validator import (
    InvestigationResultValidator,
    InvestigationValidationError,
    is_valid_investigation,
    validate_investigation,
)


# ============================================================
# Helpers
# ============================================================


def make_case(
    *,
    difference: str = "5000.00",
) -> InvestigationCase:
    difference_decimal = Decimal(difference)

    return InvestigationCase(
        case_id="CASE_0001",
        discrepancy_id="DISC_SETTLEMENT_AMOUNT",
        control_failure="SETTLEMENT_AMOUNT",
        affected_event_ids=[
            "PAYMENT_1",
            "SETTLEMENT_1",
        ],
        expected_value=Decimal("50000.00"),
        observed_value=(
            Decimal("50000.00")
            - difference_decimal
        ),
        difference=difference_decimal,
        expected_state={
            "gross_captured": Decimal("50000.00"),
            "expected_settlement": Decimal(
                "50000.00"
            ),
        },
        observed_state={
            "gross_captured": Decimal("50000.00"),
            "total_settled": (
                Decimal("50000.00")
                - difference_decimal
            ),
        },
    )


def make_finding(
    *,
    hypothesis_type=HypothesisType.REFUND,
    status=HypothesisStatus.SUPPORTED,
    explained_amount: str = "5000.00",
    evidence_ids=None,
    contradicting_evidence_ids=None,
):
    return HypothesisFinding(
        hypothesis_type=hypothesis_type,
        status=status,
        explained_amount=Decimal(
            explained_amount
        ),
        evidence_ids=(
            evidence_ids
            if evidence_ids is not None
            else ["EVIDENCE_1"]
        ),
        contradicting_evidence_ids=(
            contradicting_evidence_ids
            if contradicting_evidence_ids is not None
            else []
        ),
        reasoning="Test finding.",
    )


def make_result(
    case: InvestigationCase,
    *,
    status=InvestigationStatus.RESOLVED,
    explained_amount: str = "5000.00",
    remaining_unexplained: str = "0",
    hypotheses=None,
    supporting_evidence_ids=None,
    validated: bool = False,
):
    if hypotheses is None:
        hypotheses = [
            make_finding(
                explained_amount=explained_amount,
            )
        ]

    if supporting_evidence_ids is None:
        supporting_evidence_ids = [
            "EVIDENCE_1"
        ]

    return InvestigationResult(
        investigation_id=(
            "INV_CASE_0001_DISC_SETTLEMENT_AMOUNT"
        ),
        case_id=case.case_id,
        discrepancy_id=case.discrepancy_id,
        status=status,
        hypotheses=hypotheses,
        explained_amount=Decimal(
            explained_amount
        ),
        remaining_unexplained=Decimal(
            remaining_unexplained
        ),
        supporting_evidence_ids=(
            supporting_evidence_ids
        ),
        conclusion="Test conclusion.",
        validated=validated,
    )


# ============================================================
# Basic validation
# ============================================================


def test_valid_resolved_result_passes_validation():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.RESOLVED,
        explained_amount="5000.00",
        remaining_unexplained="0",
    )

    validated = InvestigationResultValidator().validate(
        case,
        result,
    )

    assert validated.validated is True
    assert result.validated is False


def test_validated_result_preserves_all_other_fields():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.RESOLVED,
        explained_amount="5000.00",
        remaining_unexplained="0",
    )

    validated = InvestigationResultValidator().validate(
        case,
        result,
    )

    assert (
        validated.investigation_id
        == result.investigation_id
    )

    assert validated.case_id == result.case_id

    assert (
        validated.discrepancy_id
        == result.discrepancy_id
    )

    assert (
        validated.status
        == result.status
    )

    assert (
        validated.explained_amount
        == result.explained_amount
    )

    assert (
        validated.remaining_unexplained
        == result.remaining_unexplained
    )

    assert (
        validated.supporting_evidence_ids
        == result.supporting_evidence_ids
    )


# ============================================================
# Identity validation
# ============================================================


def test_mismatched_case_id_is_rejected():
    case = make_case()

    result = make_result(case)

    result = result.model_copy(
        update={
            "case_id": "CASE_OTHER"
        }
    )

    with pytest.raises(
        InvestigationValidationError,
        match="case_id",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_mismatched_discrepancy_id_is_rejected():
    case = make_case()

    result = make_result(case)

    result = result.model_copy(
        update={
            "discrepancy_id": "DISC_OTHER"
        }
    )

    with pytest.raises(
        InvestigationValidationError,
        match="discrepancy_id",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


# ============================================================
# Amount validation
# ============================================================


def test_negative_explained_amount_is_rejected():
    case = make_case()

    result = make_result(
        case,
        explained_amount="-100.00",
        remaining_unexplained="5100.00",
    )

    with pytest.raises(
        InvestigationValidationError,
        match="explained_amount cannot be negative",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_negative_remaining_amount_is_rejected():
    case = make_case()

    result = make_result(
        case,
        explained_amount="5000.00",
        remaining_unexplained="-1.00",
    )

    with pytest.raises(
        InvestigationValidationError,
        match="remaining_unexplained cannot be negative",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_explained_amount_cannot_exceed_discrepancy():
    case = make_case(
        difference="5000.00"
    )

    result = make_result(
        case,
        explained_amount="6000.00",
        remaining_unexplained="0",
    )

    with pytest.raises(
        InvestigationValidationError,
        match="explained_amount cannot exceed",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_explained_and_remaining_amounts_must_reconcile():
    case = make_case(
        difference="5000.00"
    )

    result = make_result(
        case,
        explained_amount="2000.00",
        remaining_unexplained="2000.00",
        status=InvestigationStatus.UNRESOLVED,
    )

    with pytest.raises(
        InvestigationValidationError,
        match="must equal absolute discrepancy",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_zero_difference_requires_zero_explanation():
    case = make_case(
        difference="0"
    )

    result = make_result(
        case,
        status=InvestigationStatus.RESOLVED,
        explained_amount="0",
        remaining_unexplained="0",
        hypotheses=[],
        supporting_evidence_ids=[],
    )

    validated = InvestigationResultValidator().validate(
        case,
        result,
    )

    assert validated.validated is True


# ============================================================
# Status invariants
# ============================================================


def test_resolved_requires_zero_remaining_amount():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.RESOLVED,
        explained_amount="4000.00",
        remaining_unexplained="1000.00",
    )

    with pytest.raises(
        InvestigationValidationError,
        match="RESOLVED.*zero",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_resolved_requires_complete_explanation():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.RESOLVED,
        explained_amount="4000.00",
        remaining_unexplained="1000.00",
    )

    with pytest.raises(
        InvestigationValidationError,
        match="RESOLVED.*complete",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_insufficient_evidence_requires_zero_explained_amount():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        explained_amount="1000.00",
        remaining_unexplained="4000.00",
        hypotheses=[],
        supporting_evidence_ids=[],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="INSUFFICIENT_EVIDENCE",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_contradiction_requires_zero_explained_amount():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.CONTRADICTION,
        explained_amount="1000.00",
        remaining_unexplained="4000.00",
        hypotheses=[
            make_finding(
                status=HypothesisStatus.CONTRADICTED,
                explained_amount="0",
                evidence_ids=[],
            )
        ],
        supporting_evidence_ids=[],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="CONTRADICTION",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


# ============================================================
# Hypothesis invariants
# ============================================================


def test_negative_hypothesis_amount_is_rejected():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.UNRESOLVED,
        explained_amount="0",
        remaining_unexplained="5000.00",
        hypotheses=[
            make_finding(
                explained_amount="-100.00",
            )
        ],
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="hypothesis explained_amount",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_hypothesis_amount_cannot_exceed_discrepancy():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.RESOLVED,
        explained_amount="5000.00",
        remaining_unexplained="0",
        hypotheses=[
            make_finding(
                explained_amount="6000.00",
            )
        ],
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="hypothesis explained_amount cannot exceed",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_contradicted_hypothesis_cannot_have_supporting_evidence():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.CONTRADICTION,
        explained_amount="0",
        remaining_unexplained="5000.00",
        hypotheses=[
            make_finding(
                status=HypothesisStatus.CONTRADICTED,
                explained_amount="0",
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="CONTRADICTED hypothesis",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


# ============================================================
# Evidence invariants
# ============================================================


def test_duplicate_hypothesis_evidence_is_rejected():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.UNRESOLVED,
        explained_amount="2000.00",
        remaining_unexplained="3000.00",
        hypotheses=[
            make_finding(
                explained_amount="1000.00",
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            ),
            make_finding(
                explained_amount="1000.00",
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            ),
        ],
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="cannot be duplicated across",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_duplicate_result_evidence_is_rejected():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.UNRESOLVED,
        explained_amount="2000.00",
        remaining_unexplained="3000.00",
        hypotheses=[
            make_finding(
                explained_amount="2000.00",
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        supporting_evidence_ids=[
            "EVIDENCE_1",
            "EVIDENCE_1",
        ],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="result supporting evidence IDs",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


def test_result_evidence_must_match_finding_evidence():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.UNRESOLVED,
        explained_amount="2000.00",
        remaining_unexplained="3000.00",
        hypotheses=[
            make_finding(
                explained_amount="2000.00",
                evidence_ids=[
                    "EVIDENCE_A"
                ],
            )
        ],
        supporting_evidence_ids=[
            "EVIDENCE_B"
        ],
    )

    with pytest.raises(
        InvestigationValidationError,
        match="must match",
    ):
        InvestigationResultValidator().validate(
            case,
            result,
        )


# ============================================================
# Positive unresolved case
# ============================================================


def test_valid_partial_investigation_passes():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.UNRESOLVED,
        explained_amount="2000.00",
        remaining_unexplained="3000.00",
        hypotheses=[
            make_finding(
                status=HypothesisStatus.WEAKLY_SUPPORTED,
                explained_amount="2000.00",
                evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        supporting_evidence_ids=[
            "EVIDENCE_1"
        ],
    )

    validated = InvestigationResultValidator().validate(
        case,
        result,
    )

    assert validated.validated is True
    assert (
        validated.status
        == InvestigationStatus.UNRESOLVED
    )


# ============================================================
# Positive insufficient-evidence case
# ============================================================


def test_valid_insufficient_evidence_result_passes():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        explained_amount="0",
        remaining_unexplained="5000.00",
        hypotheses=[],
        supporting_evidence_ids=[],
    )

    validated = InvestigationResultValidator().validate(
        case,
        result,
    )

    assert validated.validated is True


# ============================================================
# Contradiction positive case
# ============================================================


def test_valid_contradiction_result_passes():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.CONTRADICTION,
        explained_amount="0",
        remaining_unexplained="5000.00",
        hypotheses=[
            make_finding(
                status=HypothesisStatus.CONTRADICTED,
                explained_amount="0",
                evidence_ids=[],
                contradicting_evidence_ids=[
                    "EVIDENCE_CONTRADICTION"
                ],
            )
        ],
        supporting_evidence_ids=[],
    )

    validated = InvestigationResultValidator().validate(
        case,
        result,
    )

    assert validated.validated is True


# ============================================================
# Convenience APIs
# ============================================================


def test_validate_investigation_convenience_function():
    case = make_case()

    result = make_result(case)

    validated = validate_investigation(
        case,
        result,
    )

    assert validated.validated is True


def test_is_valid_investigation_returns_true_for_valid_result():
    case = make_case()

    result = make_result(case)

    assert is_valid_investigation(
        case,
        result,
    ) is True


def test_is_valid_investigation_returns_false_for_invalid_result():
    case = make_case()

    result = make_result(
        case,
        explained_amount="4000.00",
        remaining_unexplained="500.00",
    )

    # The result is numerically consistent but RESOLVED is
    # invalid because it does not fully explain the discrepancy.
    assert is_valid_investigation(
        case,
        result,
    ) is False


# ============================================================
# Non-mutating behavior
# ============================================================


def test_validator_does_not_mutate_original_result():
    case = make_case()

    result = make_result(
        case,
        validated=False,
    )

    before = result.model_dump()

    validated = InvestigationResultValidator().validate(
        case,
        result,
    )

    after = result.model_dump()

    assert after == before
    assert result.validated is False
    assert validated.validated is True


# ============================================================
# Multiple validation errors
# ============================================================


def test_validator_reports_multiple_errors_together():
    case = make_case()

    result = make_result(
        case,
        status=InvestigationStatus.RESOLVED,
        explained_amount="6000.00",
        remaining_unexplained="1000.00",
        hypotheses=[
            make_finding(
                explained_amount="6000.00",
                evidence_ids=[
                    "EVIDENCE_1",
                    "EVIDENCE_1",
                ],
            )
        ],
        supporting_evidence_ids=[
            "EVIDENCE_1",
            "EVIDENCE_1",
        ],
    )

    with pytest.raises(
        InvestigationValidationError
    ) as exc_info:
        InvestigationResultValidator().validate(
            case,
            result,
        )

    message = str(
        exc_info.value
    )

    assert "explained_amount" in message
    assert "RESOLVED" in message
    assert "duplicate" in message.lower()