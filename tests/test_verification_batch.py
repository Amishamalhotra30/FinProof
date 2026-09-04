from decimal import Decimal

from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.reconstruction.result import (
    ReconstructionResult,
)
from app.verification.batch import (
    BatchFinancialStateVerifier,
    BatchVerificationResult,
    verify_batch,
)
from app.verification.models import (
    VerificationStatus,
)


def make_reconstruction(
    settlement: str = "47500.00",
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
            "47500.00"
        ),
    )

    return ReconstructionResult(
        event_graph=None,
        chains=(),
        chain_states=(),
        batch_state=state,
    )


def test_empty_batch():
    result = BatchFinancialStateVerifier().verify(
        []
    )

    assert isinstance(
        result,
        BatchVerificationResult,
    )

    assert result.total_cases == 0
    assert result.verified_cases == 0
    assert result.failed_cases == 0
    assert result.pending_cases == 0
    assert result.total_discrepancies == 0


def test_batch_verifies_all_valid_cases():
    reconstructions = [
        make_reconstruction(),
        make_reconstruction(),
        make_reconstruction(),
    ]

    result = BatchFinancialStateVerifier().verify(
        reconstructions
    )

    assert result.total_cases == 3
    assert result.verified_cases == 3
    assert result.failed_cases == 0
    assert result.pending_cases == 0
    assert result.total_discrepancies == 0


def test_batch_detects_failed_cases():
    reconstructions = [
        make_reconstruction(),
        make_reconstruction(
            settlement="47000.00"
        ),
        make_reconstruction(),
    ]

    result = BatchFinancialStateVerifier().verify(
        reconstructions
    )

    assert result.total_cases == 3
    assert result.verified_cases == 2
    assert result.failed_cases == 1
    assert result.total_discrepancies == 1


def test_batch_exposes_all_discrepancies():
    reconstructions = [
        make_reconstruction(
            settlement="47000.00"
        ),
        make_reconstruction(
            settlement="46000.00"
        ),
    ]

    result = BatchFinancialStateVerifier().verify(
        reconstructions
    )

    assert result.total_discrepancies == 2

    assert all(
        discrepancy.control_id
        == "SETTLEMENT_AMOUNT"
        for discrepancy
        in result.discrepancies
    )


def test_batch_verification_rate():
    reconstructions = [
        make_reconstruction(),
        make_reconstruction(
            settlement="47000.00"
        ),
        make_reconstruction(),
        make_reconstruction(
            settlement="46000.00"
        ),
    ]

    result = BatchFinancialStateVerifier().verify(
        reconstructions
    )

    assert (
        result.verification_rate
        == Decimal("0.5")
    )

    assert (
        result.failure_rate
        == Decimal("0.5")
    )


def test_batch_processing_time_is_recorded():
    result = BatchFinancialStateVerifier().verify(
        [
            make_reconstruction(),
            make_reconstruction(),
        ]
    )

    assert result.processing_time_ms >= Decimal(
        "0"
    )


def test_batch_preserves_individual_results():
    reconstructions = [
        make_reconstruction(),
        make_reconstruction(
            settlement="47000.00"
        ),
    ]

    result = BatchFinancialStateVerifier().verify(
        reconstructions
    )

    assert len(result.results) == 2

    assert (
        result.results[0].status
        == VerificationStatus.VERIFIED
    )

    assert (
        result.results[1].status
        == VerificationStatus.FAILED
    )


def test_convenience_function_matches_service():
    result = verify_batch(
        [
            make_reconstruction(),
            make_reconstruction(
                settlement="47000.00"
            ),
        ]
    )

    assert result.total_cases == 2
    assert result.verified_cases == 1
    assert result.failed_cases == 1