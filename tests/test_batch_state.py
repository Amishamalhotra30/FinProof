from decimal import Decimal

from app.reconstruction.batch_state import (
    BatchStateReconstructor,
)
from app.reconstruction.event_chain import EventChain
from app.reconstruction.state_reconstructor import (
    ObservedFinancialState,
)


def make_state(
    chain_id: str,
    gross: str = "0",
    refund: str = "0",
    fee: str = "0",
    adjustment: str = "0",
    settlement: str = "0",
    bank: str = "0",
    payments: tuple[str, ...] = (),
    refunds: tuple[str, ...] = (),
    fees: tuple[str, ...] = (),
    adjustments: tuple[str, ...] = (),
    settlements: tuple[str, ...] = (),
    banks: tuple[str, ...] = (),
):
    return ObservedFinancialState(
        chain_id=chain_id,
        gross_amount=Decimal(gross),
        refund_amount=Decimal(refund),
        fee_amount=Decimal(fee),
        adjustment_amount=Decimal(adjustment),
        settlement_amount=Decimal(settlement),
        bank_credit_amount=Decimal(bank),
        payment_event_ids=payments,
        refund_event_ids=refunds,
        fee_event_ids=fees,
        adjustment_event_ids=adjustments,
        settlement_event_ids=settlements,
        bank_event_ids=banks,
    )


def test_aggregate_empty_states():

    result = BatchStateReconstructor.aggregate(
        []
    )

    assert result.chain_count == 0
    assert result.total_gross_amount == Decimal("0")
    assert result.total_refund_amount == Decimal("0")
    assert result.total_fee_amount == Decimal("0")
    assert result.total_settlement_amount == Decimal("0")
    assert result.total_bank_credit_amount == Decimal("0")


def test_aggregate_multiple_chains():

    first = make_state(
        "CHAIN_1",
        gross="50000",
        refund="5000",
        fee="500",
        settlement="44500",
        bank="44500",
        payments=("P1",),
        refunds=("R1",),
        fees=("F1",),
        settlements=("S1",),
        banks=("B1",),
    )

    second = make_state(
        "CHAIN_2",
        gross="20000",
        refund="2000",
        fee="200",
        adjustment="100",
        settlement="17900",
        bank="17900",
        payments=("P2",),
        refunds=("R2",),
        fees=("F2",),
        adjustments=("A1",),
        settlements=("S2",),
        banks=("B2",),
    )

    result = BatchStateReconstructor.aggregate(
        [
            first,
            second,
        ]
    )

    assert result.chain_count == 2

    assert result.total_gross_amount == Decimal(
        "70000"
    )

    assert result.total_refund_amount == Decimal(
        "7000"
    )

    assert result.total_fee_amount == Decimal(
        "700"
    )

    assert result.total_adjustment_amount == Decimal(
        "100"
    )

    assert result.total_settlement_amount == Decimal(
        "62400"
    )

    assert result.total_bank_credit_amount == Decimal(
        "62400"
    )


def test_total_observed_net_amount():

    state = make_state(
        "CHAIN_1",
        gross="50000",
        refund="5000",
        fee="500",
        adjustment="100",
    )

    result = BatchStateReconstructor.aggregate(
        [state]
    )

    assert result.total_observed_net_amount == (
        Decimal("44600")
    )


def test_event_counts_are_aggregated():

    first = make_state(
        "CHAIN_1",
        payments=("P1",),
        refunds=("R1", "R2"),
        fees=("F1",),
        settlements=("S1",),
        banks=("B1",),
    )

    second = make_state(
        "CHAIN_2",
        payments=("P2", "P3"),
        refunds=("R3",),
        fees=("F2", "F3"),
        adjustments=("A1", "A2"),
        settlements=("S2", "S3"),
        banks=("B2",),
    )

    result = BatchStateReconstructor.aggregate(
        [
            first,
            second,
        ]
    )

    assert result.payment_event_count == 3
    assert result.refund_event_count == 3
    assert result.fee_event_count == 3
    assert result.adjustment_event_count == 2
    assert result.settlement_event_count == 3
    assert result.bank_event_count == 2


def test_reconstruct_uses_state_reconstructor():

    chain = EventChain(
        chain_id="CHAIN_1",
        event_ids=[],
    )

    result = BatchStateReconstructor().reconstruct(
        [chain],
        [],
    )

    assert result.chain_count == 1

    assert result.total_gross_amount == Decimal(
        "0"
    )


def test_aggregation_does_not_modify_states():

    state = make_state(
        "CHAIN_1",
        gross="50000",
        payments=("P1",),
    )

    before = state

    result = BatchStateReconstructor.aggregate(
        [state]
    )

    assert state == before
    assert result.total_gross_amount == Decimal(
        "50000"
    )


def test_adjustment_increases_observed_net():

    state = make_state(
        "CHAIN_1",
        gross="10000",
        adjustment="250",
    )

    result = BatchStateReconstructor.aggregate(
        [state]
    )

    assert result.total_observed_net_amount == (
        Decimal("10250")
    )