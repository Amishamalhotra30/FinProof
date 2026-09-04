from decimal import Decimal
from app.verification.models import (
    ControlStatus,
    VerificationStatus,
)
from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.reconstruction.result import ReconstructionResult
from app.verification.models import (
    VerificationStatus,
)
from app.verification.verifier import (
    FinancialStateVerifier,
    verify_reconstruction,
)


def make_reconstruction(
    settlement: str = "47500.00",
    bank_credit: str = "47500.00",
) -> ReconstructionResult:
    state = BatchReconstructionState(
        chain_count=1,
        total_gross_amount=Decimal("50000.00"),
        total_refund_amount=Decimal("2000.00"),
        total_fee_amount=Decimal("1000.00"),
        total_adjustment_amount=Decimal("500.00"),
        total_settlement_amount=Decimal(
            settlement
        ),
        total_bank_credit_amount=Decimal(
            bank_credit
        ),
    )

    return ReconstructionResult(
        event_graph=None,
        chains=(),
        chain_states=(),
        batch_state=state,
    )


def test_verifier_passes_valid_state():
    reconstruction = make_reconstruction()

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    assert (
        result.status
        == VerificationStatus.VERIFIED
    )

    assert result.discrepancies == []


def test_verifier_detects_settlement_failure():
    reconstruction = make_reconstruction(
        settlement="47000.00",
    )

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    assert (
        result.status
        == VerificationStatus.FAILED
    )

    assert len(result.discrepancies) == 1

    assert (
        result.discrepancies[0].control_id
        == "SETTLEMENT_AMOUNT"
    )

def test_verifier_keeps_bank_check_pending_when_expected_value_is_unavailable():
    reconstruction = make_reconstruction(
        bank_credit="47000.00",
    )

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    assert (
        result.status
        == VerificationStatus.VERIFIED
    )

    bank_control = next(
        control
        for control in result.controls
        if control.control_id
        == "BANK_CREDIT_AMOUNT"
    )

    assert (
        bank_control.status
        == ControlStatus.PENDING
    )

    assert (
        bank_control.expected_value
        is None
    )

    assert (
        bank_control.observed_value
        is None
    )

    assert not any(
        discrepancy.control_id
        == "BANK_CREDIT_AMOUNT"
        for discrepancy
        in result.discrepancies
    )

def test_verifier_calculates_expected_state():
    reconstruction = make_reconstruction()

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    assert (
        result.expected_state.expected_settlement
        == Decimal("47500.00")
    )


def test_verifier_preserves_observed_state():
    reconstruction = make_reconstruction()

    before = reconstruction.batch_state

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    assert (
        reconstruction.batch_state
        == before
    )

    assert (
        result.observed_state[
            "total_settled"
        ]
        == Decimal("47500.00")
    )


def test_convenience_function_matches_service():
    reconstruction = make_reconstruction()

    result = verify_reconstruction(
        reconstruction
    )

    assert (
        result.status
        == VerificationStatus.VERIFIED
    )


def test_processing_time_is_recorded():
    reconstruction = make_reconstruction()

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    assert (
        result.processing_time_ms is not None
    )

    assert (
        result.processing_time_ms
        >= Decimal("0")
    )


def test_verifier_returns_all_controls():
    reconstruction = make_reconstruction()

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    expected_control_ids = {
    # Amount / accounting controls
    "SETTLEMENT_AMOUNT",
    "BANK_CREDIT_AMOUNT",
    "REFUND_AMOUNT",
    "FEE_AMOUNT",
    "ADJUSTMENT_AMOUNT",

    # Temporal / lifecycle controls
    "EVENT_ORDERING",
    "SETTLEMENT_TIMING",
    "BANK_AFTER_SETTLEMENT",
    "CHAIN_TEMPORAL_ORDER",

    # Completeness controls
    "PAYMENT_SETTLEMENT_COMPLETENESS",
    "REFUND_PAYMENT_COMPLETENESS",
    "SETTLEMENT_BANK_COMPLETENESS",

    # Duplicate protection
    "DUPLICATE_EVENT",

    # Currency consistency
    "CURRENCY_CONSISTENCY",
    }

    actual_control_ids = {
        control.control_id
        for control in result.controls
    }

    assert actual_control_ids == expected_control_ids

def test_verifier_includes_temporal_controls():
    reconstruction = make_reconstruction()

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    control_ids = {
        control.control_id
        for control in result.controls
    }

    assert {
        "EVENT_ORDERING",
        "SETTLEMENT_TIMING",
        "BANK_AFTER_SETTLEMENT",
        "CHAIN_TEMPORAL_ORDER",
    }.issubset(control_ids)
def test_verifier_reports_temporal_failure():
    from datetime import datetime

    from app.domain.enums import (
        EventType,
        RecordSource,
    )
    from app.domain.events import FinancialEvent
    from app.domain.graph import EventGraph

    graph = EventGraph()

    settlement = FinancialEvent(
        event_id="SETTLEMENT_1",
        event_type=EventType.SETTLEMENT_PROCESSED,
        entity_id="PAYMENT_1",
        amount=Decimal("47500.00"),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            30,
            10,
            0,
        ),
        related_event_ids=["PAYMENT_1"],
        source=RecordSource.SETTLEMENT,
        metadata={},
    )

    payment = FinancialEvent(
        event_id="PAYMENT_1",
        event_type=EventType.PAYMENT_CAPTURED,
        entity_id="PAYMENT_1",
        amount=Decimal("50000.00"),
        currency="INR",
        timestamp=datetime(
            2026,
            8,
            30,
            11,
            0,
        ),
        related_event_ids=[],
        source=RecordSource.PAYMENT,
        metadata={},
    )

    graph.add_event(settlement)
    graph.add_event(payment)

    from app.reconstruction.result import ReconstructionResult

    reconstruction = ReconstructionResult(
        event_graph=graph,
        chains=(),
        chain_states=(),
        batch_state=make_reconstruction().batch_state,
    )

    result = FinancialStateVerifier().verify(
        reconstruction
    )

    ordering_control = next(
        control
        for control in result.controls
        if control.control_id == "EVENT_ORDERING"
    )

    assert (
        ordering_control.status
        == ControlStatus.FAIL
    )

    assert (
        result.status
        == VerificationStatus.FAILED
    )
