from decimal import Decimal
from unittest.mock import Mock

from app.domain.graph import EventGraph
from app.investigation.models import (
    InvestigationCase,
    InvestigationResult,
    InvestigationStatus,
)
from app.investigation.service import (
    InvestigationService,
    investigate_case,
)


def make_case() -> InvestigationCase:
    return InvestigationCase(
        case_id="CASE_001",
        discrepancy_id="DISC_SETTLEMENT_AMOUNT",
        control_failure="SETTLEMENT_AMOUNT",
        affected_event_ids=[
            "PAYMENT_1",
        ],
        expected_value=Decimal("50000.00"),
        observed_value=Decimal("45000.00"),
        difference=Decimal("-5000.00"),
        expected_state={
            "expected_settlement": Decimal("50000.00"),
        },
        observed_state={
            "total_settlement_amount": Decimal("45000.00"),
        },
    )


def make_result() -> InvestigationResult:
    return InvestigationResult(
        investigation_id="INV_CASE_001_DISC_SETTLEMENT_AMOUNT",
        case_id="CASE_001",
        discrepancy_id="DISC_SETTLEMENT_AMOUNT",
        status=InvestigationStatus.UNRESOLVED,
        hypotheses=[],
        explained_amount=Decimal("0"),
        remaining_unexplained=Decimal("5000.00"),
        supporting_evidence_ids=[],
        conclusion="Insufficient evidence.",
        validated=False,
    )


def test_service_returns_investigation_result():

    orchestrator = Mock()

    orchestrator.investigate.return_value = (
        make_result()
    )

    service = InvestigationService(
        orchestrator=orchestrator,
    )

    result = service.investigate(
        make_case(),
        EventGraph(),
    )

    assert result is not None
    assert result.result is not None


def test_service_exposes_result_properties():

    orchestrator = Mock()

    orchestrator.investigate.return_value = (
        make_result()
    )

    result = InvestigationService(
        orchestrator=orchestrator,
    ).investigate(
        make_case(),
        EventGraph(),
    )

    assert (
        result.investigation_id
        == "INV_CASE_001_DISC_SETTLEMENT_AMOUNT"
    )

    assert result.case_id == "CASE_001"

    assert (
        result.discrepancy_id
        == "DISC_SETTLEMENT_AMOUNT"
    )

    assert (
        result.status
        == InvestigationStatus.UNRESOLVED
    )

    assert (
        result.explained_amount
        == Decimal("0")
    )

    assert (
        result.remaining_unexplained
        == Decimal("5000.00")
    )


def test_service_delegates_to_orchestrator():

    orchestrator = Mock()

    orchestrator.investigate.return_value = (
        make_result()
    )

    case = make_case()
    graph = EventGraph()

    InvestigationService(
        orchestrator=orchestrator,
    ).investigate(
        case,
        graph,
    )

    orchestrator.investigate.assert_called_once_with(
        case,
        graph,
    )


def test_service_does_not_automatically_validate():

    orchestrator = Mock()

    result = make_result()

    orchestrator.investigate.return_value = result

    service_result = InvestigationService(
        orchestrator=orchestrator,
    ).investigate(
        make_case(),
        EventGraph(),
    )

    assert service_result.validated is False


def test_service_preserves_underlying_result():

    orchestrator = Mock()

    expected_result = make_result()

    orchestrator.investigate.return_value = (
        expected_result
    )

    service_result = InvestigationService(
        orchestrator=orchestrator,
    ).investigate(
        make_case(),
        EventGraph(),
    )

    assert service_result.result is expected_result


def test_service_does_not_mutate_graph():

    orchestrator = Mock()

    orchestrator.investigate.return_value = (
        make_result()
    )

    graph = EventGraph()

    before = dict(graph.events)

    InvestigationService(
        orchestrator=orchestrator,
    ).investigate(
        make_case(),
        graph,
    )

    assert graph.events == before


def test_convenience_function_uses_service():

    result = investigate_case(
        make_case(),
        EventGraph(),
    )

    assert result is not None