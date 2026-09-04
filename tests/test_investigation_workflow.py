from decimal import Decimal
from unittest.mock import Mock

from app.domain.graph import EventGraph
from app.investigation.models import (
    InvestigationResult,
    InvestigationStatus,
)
from app.investigation.service import (
    InvestigationServiceResult,
)
from app.investigation.workflow import (
    InvestigationWorkflow,
    InvestigationWorkflowResult,
    investigate_verification,
)
from app.verification.models import (
    ControlStatus,
    Discrepancy,
    ExpectedFinancialState,
    Materiality,
    VerificationResult,
    VerificationStatus,
)


# ============================================================
# Helpers
# ============================================================


def make_discrepancy(
    discrepancy_id: str,
    difference: str = "5000.00",
) -> Discrepancy:
    return Discrepancy(
        discrepancy_id=discrepancy_id,
        control_id="SETTLEMENT_AMOUNT",
        expected_value=Decimal("50000.00"),
        observed_value=(
            Decimal("50000.00")
            - Decimal(difference)
        ),
        difference=Decimal(difference),
        relative_difference=Decimal("0.10"),
        affected_event_ids=[
            f"{discrepancy_id}_EVENT",
        ],
        evidence_references=[],
        materiality=Materiality.HIGH,
        blocking=True,
    )


def make_verification(
    discrepancies=None,
) -> VerificationResult:

    if discrepancies is None:
        discrepancies = []

    return VerificationResult(
        case_id="CASE_001",
        status=VerificationStatus.FAILED,
        observed_state={
            "total_settlement_amount": Decimal(
                "45000.00"
            ),
        },
        expected_state=ExpectedFinancialState(
            gross_captured=Decimal("50000.00"),
            expected_settlement=Decimal(
                "50000.00"
            ),
        ),
        controls=[],
        discrepancies=discrepancies,
    )


def make_result(
    case_id: str = "CASE_001",
    discrepancy_id: str = "DISC_001",
) -> InvestigationResult:
    return InvestigationResult(
        investigation_id=(
            f"INV_{case_id}_{discrepancy_id}"
        ),
        case_id=case_id,
        discrepancy_id=discrepancy_id,
        status=InvestigationStatus.INSUFFICIENT_EVIDENCE,
        hypotheses=[],
        explained_amount=Decimal("0"),
        remaining_unexplained=Decimal(
            "5000.00"
        ),
        supporting_evidence_ids=[],
        conclusion=(
            "The available evidence is insufficient."
        ),
        validated=False,
    )


def make_service_result(
    discrepancy_id: str,
) -> InvestigationServiceResult:

    return InvestigationServiceResult(
        result=make_result(
            discrepancy_id=discrepancy_id,
        )
    )


# ============================================================
# Empty workflow
# ============================================================


def test_empty_verification_produces_no_cases():

    verification = make_verification()

    result = InvestigationWorkflow().investigate(
        verification,
        EventGraph(),
    )

    assert result.cases == ()
    assert result.results == ()
    assert result.count == 0


def test_empty_verification_produces_no_investigation_results():

    verification = make_verification()

    result = InvestigationWorkflow().investigate(
        verification,
        EventGraph(),
    )

    assert result.investigation_results == ()


# ============================================================
# Case creation
# ============================================================


def test_workflow_builds_one_case_per_discrepancy():

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
            make_discrepancy("DISC_002"),
            make_discrepancy("DISC_003"),
        ]
    )

    result = InvestigationWorkflow().investigate(
        verification,
        EventGraph(),
    )

    assert len(result.cases) == 3

    assert [
        case.discrepancy_id
        for case in result.cases
    ] == [
        "DISC_001",
        "DISC_002",
        "DISC_003",
    ]


def test_workflow_preserves_case_id():

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
        ]
    )

    result = InvestigationWorkflow().investigate(
        verification,
        EventGraph(),
    )

    assert result.cases[0].case_id == (
        "CASE_001"
    )


def test_workflow_preserves_affected_event_ids():

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
        ]
    )

    result = InvestigationWorkflow().investigate(
        verification,
        EventGraph(),
    )

    assert result.cases[0].affected_event_ids == [
        "DISC_001_EVENT",
    ]


# ============================================================
# Service delegation
# ============================================================


def test_workflow_delegates_each_case_to_service():

    service = Mock()

    service.investigate.side_effect = [
        make_service_result("DISC_001"),
        make_service_result("DISC_002"),
    ]

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
            make_discrepancy("DISC_002"),
        ]
    )

    workflow = InvestigationWorkflow(
        investigation_service=service,
    )

    result = workflow.investigate(
        verification,
        EventGraph(),
    )

    assert service.investigate.call_count == 2

    assert [
        call.args[0].discrepancy_id
        for call in service.investigate.call_args_list
    ] == [
        "DISC_001",
        "DISC_002",
    ]

    assert len(result.results) == 2


def test_workflow_passes_same_graph_to_each_investigation():

    service = Mock()

    service.investigate.side_effect = [
        make_service_result("DISC_001"),
        make_service_result("DISC_002"),
    ]

    graph = EventGraph()

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
            make_discrepancy("DISC_002"),
        ]
    )

    InvestigationWorkflow(
        investigation_service=service,
    ).investigate(
        verification,
        graph,
    )

    for call in service.investigate.call_args_list:
        assert call.args[1] is graph


# ============================================================
# Result ordering
# ============================================================


def test_workflow_preserves_result_order():

    service = Mock()

    service.investigate.side_effect = [
        make_service_result("DISC_A"),
        make_service_result("DISC_B"),
        make_service_result("DISC_C"),
    ]

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_A"),
            make_discrepancy("DISC_B"),
            make_discrepancy("DISC_C"),
        ]
    )

    result = InvestigationWorkflow(
        investigation_service=service,
    ).investigate(
        verification,
        EventGraph(),
    )

    assert [
        item.discrepancy_id
        for item in result.results
    ] == [
        "DISC_A",
        "DISC_B",
        "DISC_C",
    ]


# ============================================================
# Result preservation
# ============================================================


def test_workflow_preserves_service_results():

    service = Mock()

    first = make_service_result(
        "DISC_001"
    )

    second = make_service_result(
        "DISC_002"
    )

    service.investigate.side_effect = [
        first,
        second,
    ]

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
            make_discrepancy("DISC_002"),
        ]
    )

    result = InvestigationWorkflow(
        investigation_service=service,
    ).investigate(
        verification,
        EventGraph(),
    )

    assert result.results[0] is first
    assert result.results[1] is second


def test_workflow_exposes_underlying_investigation_results():

    service = Mock()

    first = make_service_result(
        "DISC_001"
    )

    second = make_service_result(
        "DISC_002"
    )

    service.investigate.side_effect = [
        first,
        second,
    ]

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
            make_discrepancy("DISC_002"),
        ]
    )

    result = InvestigationWorkflow(
        investigation_service=service,
    ).investigate(
        verification,
        EventGraph(),
    )

    assert result.investigation_results == (
        first.result,
        second.result,
    )


# ============================================================
# No mutation
# ============================================================


def test_workflow_does_not_modify_verification():

    discrepancies = [
        make_discrepancy("DISC_001"),
        make_discrepancy("DISC_002"),
    ]

    verification = make_verification(
        discrepancies=discrepancies,
    )

    before = verification.model_dump(
        mode="python"
    )

    InvestigationWorkflow(
        investigation_service=Mock(
            investigate=Mock(
                side_effect=[
                    make_service_result(
                        "DISC_001"
                    ),
                    make_service_result(
                        "DISC_002"
                    ),
                ]
            )
        )
    ).investigate(
        verification,
        EventGraph(),
    )

    after = verification.model_dump(
        mode="python"
    )

    assert after == before


def test_workflow_does_not_modify_graph():

    service = Mock()

    service.investigate.return_value = (
        make_service_result("DISC_001")
    )

    graph = EventGraph()

    before = dict(graph.events)

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
        ]
    )

    InvestigationWorkflow(
        investigation_service=service,
    ).investigate(
        verification,
        graph,
    )

    assert graph.events == before


# ============================================================
# Workflow result object
# ============================================================


def test_workflow_result_is_structured():

    service_result = make_service_result(
        "DISC_001"
    )

    result = InvestigationWorkflowResult(
        cases=[],
        results=[service_result],
    )

    assert result.count == 0
    assert result.results == (
        service_result,
    )

    assert result.investigation_results == (
        service_result.result,
    )


# ============================================================
# Convenience API
# ============================================================


def test_convenience_function_runs_workflow():

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
        ]
    )

    result = investigate_verification(
        verification,
        EventGraph(),
    )

    assert result.count == 1

    assert (
        result.cases[0].discrepancy_id
        == "DISC_001"
    )


# ============================================================
# Validation contract
# ============================================================


def test_workflow_does_not_automatically_validate():

    service = Mock()

    service.investigate.return_value = (
        make_service_result("DISC_001")
    )

    verification = make_verification(
        discrepancies=[
            make_discrepancy("DISC_001"),
        ]
    )

    result = InvestigationWorkflow(
        investigation_service=service,
    ).investigate(
        verification,
        EventGraph(),
    )

    assert (
        result.results[0].validated
        is False
    )