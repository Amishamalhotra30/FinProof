from decimal import Decimal

from app.investigation.models import (
    HypothesisFinding,
    HypothesisStatus,
    HypothesisType,
    InvestigationResult,
    InvestigationStatus,
)
from app.investigation.report import (
    InvestigationReport,
    InvestigationReportBuilder,
    build_investigation_report,
)


# ============================================================
# Helpers
# ============================================================


def make_result(
    *,
    status=InvestigationStatus.UNRESOLVED,
    explained_amount="2000.00",
    remaining_unexplained="3000.00",
    hypotheses=None,
    supporting_evidence_ids=None,
    validated=False,
):
    if hypotheses is None:
        hypotheses = [
            HypothesisFinding(
                hypothesis_type=HypothesisType.REFUND,
                status=HypothesisStatus.WEAKLY_SUPPORTED,
                explained_amount=Decimal(
                    explained_amount
                ),
                evidence_ids=[
                    "EVIDENCE_REFUND_1"
                ],
                contradicting_evidence_ids=[],
                reasoning=(
                    "Refund evidence explains part "
                    "of the discrepancy."
                ),
            ),
        ]

    if supporting_evidence_ids is None:
        supporting_evidence_ids = [
            "EVIDENCE_REFUND_1"
        ]

    return InvestigationResult(
        investigation_id=(
            "INV_CASE_001_DISC_001"
        ),
        case_id="CASE_001",
        discrepancy_id="DISC_001",
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
        conclusion=(
            "Partial explanation established."
        ),
        validated=validated,
    )


# ============================================================
# Basic construction
# ============================================================


def test_builder_returns_investigation_report():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    assert isinstance(
        report,
        InvestigationReport,
    )


def test_builder_preserves_identity_fields():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    assert (
        report.investigation_id
        == result.investigation_id
    )

    assert report.case_id == result.case_id

    assert (
        report.discrepancy_id
        == result.discrepancy_id
    )


def test_builder_preserves_investigation_status():

    result = make_result(
        status=InvestigationStatus.RESOLVED,
        explained_amount="5000.00",
        remaining_unexplained="0",
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert (
        report.status
        == InvestigationStatus.RESOLVED
    )


# ============================================================
# Financial values
# ============================================================


def test_builder_preserves_explanation_amounts():

    result = make_result(
        explained_amount="2000.00",
        remaining_unexplained="3000.00",
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert (
        report.explained_amount
        == Decimal("2000.00")
    )

    assert (
        report.remaining_unexplained
        == Decimal("3000.00")
    )


def test_builder_preserves_optional_discrepancy_values():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result,
        control_failure="SETTLEMENT_AMOUNT",
        expected_value=Decimal("50000.00"),
        observed_value=Decimal("45000.00"),
        difference=Decimal("-5000.00"),
    )

    assert (
        report.control_failure
        == "SETTLEMENT_AMOUNT"
    )

    assert (
        report.expected_value
        == Decimal("50000.00")
    )

    assert (
        report.observed_value
        == Decimal("45000.00")
    )

    assert (
        report.difference
        == Decimal("-5000.00")
    )


def test_builder_does_not_invent_missing_discrepancy_values():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.control_failure is None
    assert report.expected_value is None
    assert report.observed_value is None
    assert report.difference is None


# ============================================================
# Hypotheses
# ============================================================


def test_builder_preserves_hypotheses():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.hypotheses == tuple(
        result.hypotheses
    )


def test_supported_hypotheses_are_exposed():

    result = make_result(
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=HypothesisType.REFUND,
                status=HypothesisStatus.SUPPORTED,
                explained_amount=Decimal(
                    "5000.00"
                ),
                evidence_ids=[
                    "REFUND_1"
                ],
            ),
            HypothesisFinding(
                hypothesis_type=HypothesisType.FEE,
                status=HypothesisStatus.UNDETERMINED,
                explained_amount=Decimal("0"),
                evidence_ids=[],
            ),
        ],
        supporting_evidence_ids=[
            "REFUND_1"
        ],
        explained_amount="5000.00",
        remaining_unexplained="0",
        status=InvestigationStatus.RESOLVED,
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert len(
        report.supported_hypotheses
    ) == 1

    assert (
        report.supported_hypotheses[0]
        .hypothesis_type
        == HypothesisType.REFUND
    )


def test_contradicted_hypotheses_are_exposed():

    result = make_result(
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=HypothesisType.REFUND,
                status=HypothesisStatus.CONTRADICTED,
                explained_amount=Decimal("0"),
                evidence_ids=[],
                contradicting_evidence_ids=[
                    "EVIDENCE_1"
                ],
            )
        ],
        supporting_evidence_ids=[],
        explained_amount="0",
        remaining_unexplained="5000.00",
        status=InvestigationStatus.CONTRADICTION,
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert len(
        report.contradicted_hypotheses
    ) == 1

    assert (
        report.contradicted_hypotheses[0]
        .hypothesis_type
        == HypothesisType.REFUND
    )


def test_undetermined_and_unsupported_hypotheses_are_exposed():

    result = make_result(
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=HypothesisType.REFUND,
                status=HypothesisStatus.UNDETERMINED,
            ),
            HypothesisFinding(
                hypothesis_type=HypothesisType.FEE,
                status=HypothesisStatus.UNSUPPORTED,
            ),
        ],
        supporting_evidence_ids=[],
        explained_amount="0",
        remaining_unexplained="5000.00",
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert len(
        report.unresolved_hypotheses
    ) == 2


def test_hypothesis_count_is_correct():

    result = make_result(
        hypotheses=[
            HypothesisFinding(
                hypothesis_type=HypothesisType.REFUND,
                status=HypothesisStatus.SUPPORTED,
            ),
            HypothesisFinding(
                hypothesis_type=HypothesisType.FEE,
                status=HypothesisStatus.WEAKLY_SUPPORTED,
            ),
            HypothesisFinding(
                hypothesis_type=HypothesisType.TAX,
                status=HypothesisStatus.UNDETERMINED,
            ),
        ]
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.hypothesis_count == 3


# ============================================================
# Evidence
# ============================================================


def test_supporting_evidence_ids_are_preserved():

    result = make_result(
        supporting_evidence_ids=[
            "EVIDENCE_1",
            "EVIDENCE_2",
        ]
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.supporting_evidence_ids == (
        "EVIDENCE_1",
        "EVIDENCE_2",
    )


def test_supporting_evidence_count_is_correct():

    result = make_result(
        supporting_evidence_ids=[
            "EVIDENCE_1",
            "EVIDENCE_2",
            "EVIDENCE_3",
        ]
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert (
        report.supporting_evidence_count
        == 3
    )


# ============================================================
# Status properties
# ============================================================


def test_resolved_property_is_true_for_resolved_result():

    result = make_result(
        status=InvestigationStatus.RESOLVED,
        explained_amount="5000.00",
        remaining_unexplained="0",
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.resolved is True


def test_resolved_property_is_false_for_unresolved_result():

    result = make_result(
        status=InvestigationStatus.UNRESOLVED,
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.resolved is False


def test_has_unexplained_amount_is_true_when_amount_remains():

    result = make_result(
        remaining_unexplained="3000.00"
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert (
        report.has_unexplained_amount
        is True
    )


def test_has_unexplained_amount_is_false_when_fully_explained():

    result = make_result(
        status=InvestigationStatus.RESOLVED,
        explained_amount="5000.00",
        remaining_unexplained="0",
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert (
        report.has_unexplained_amount
        is False
    )


# ============================================================
# Validation state
# ============================================================


def test_builder_preserves_validation_state():

    result = make_result(
        validated=True
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.validated is True


def test_unvalidated_result_remains_unvalidated():

    result = make_result(
        validated=False
    )

    report = InvestigationReportBuilder().build(
        result
    )

    assert report.validated is False


# ============================================================
# Conclusion
# ============================================================


def test_builder_preserves_conclusion():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    assert (
        report.conclusion
        == result.conclusion
    )


# ============================================================
# Immutability / non-mutation
# ============================================================


def test_report_is_immutable():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    try:
        report.case_id = "OTHER"
    except Exception:
        pass

    assert report.case_id == "CASE_001"


def test_builder_does_not_modify_result():

    result = make_result()

    before = result.model_dump(
        mode="python"
    )

    InvestigationReportBuilder().build(
        result,
        control_failure="SETTLEMENT_AMOUNT",
        expected_value=Decimal("50000.00"),
        observed_value=Decimal("45000.00"),
        difference=Decimal("-5000.00"),
    )

    after = result.model_dump(
        mode="python"
    )

    assert before == after


# ============================================================
# Dictionary representation
# ============================================================


def test_to_dict_contains_core_fields():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    data = report.to_dict()

    assert (
        data["investigation_id"]
        == "INV_CASE_001_DISC_001"
    )

    assert data["case_id"] == "CASE_001"

    assert (
        data["discrepancy_id"]
        == "DISC_001"
    )

    assert (
        data["status"]
        == "UNRESOLVED"
    )


def test_to_dict_preserves_decimal_values():

    result = make_result(
        explained_amount="2000.00",
        remaining_unexplained="3000.00",
    )

    report = InvestigationReportBuilder().build(
        result
    )

    data = report.to_dict()

    assert (
        data["explained_amount"]
        == Decimal("2000.00")
    )

    assert (
        data["remaining_unexplained"]
        == Decimal("3000.00")
    )


def test_to_dict_serializes_hypothesis_enums():

    result = make_result()

    report = InvestigationReportBuilder().build(
        result
    )

    data = report.to_dict()

    assert (
        data["hypotheses"][0][
            "hypothesis_type"
        ]
        == "REFUND"
    )

    assert (
        data["hypotheses"][0]["status"]
        == "WEAKLY_SUPPORTED"
    )


def test_to_dict_preserves_evidence_ids():

    result = make_result(
        supporting_evidence_ids=[
            "EVIDENCE_1",
            "EVIDENCE_2",
        ]
    )

    report = InvestigationReportBuilder().build(
        result
    )

    data = report.to_dict()

    assert data[
        "supporting_evidence_ids"
    ] == [
        "EVIDENCE_1",
        "EVIDENCE_2",
    ]


# ============================================================
# Convenience API
# ============================================================


def test_convenience_function_builds_report():

    result = make_result()

    report = build_investigation_report(
        result
    )

    assert isinstance(
        report,
        InvestigationReport,
    )

    assert (
        report.investigation_id
        == result.investigation_id
    )