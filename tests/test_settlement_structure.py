from app.reconstruction.settlement_structure import (
    SettlementStructureReconstructor,
    SettlementStructureType,
)


def test_single_payment_single_settlement():

    result = (
        SettlementStructureReconstructor()
        .reconstruct(
            ["PAY_001"],
            ["SET_001"],
            1,
        )
    )

    assert (
        result.structure_type
        == SettlementStructureType.SINGLE
    )

    assert result.payment_ids == (
        "PAY_001",
    )

    assert result.settlement_ids == (
        "SET_001",
    )


def test_one_payment_multiple_settlements_is_split():

    result = (
        SettlementStructureReconstructor()
        .reconstruct(
            ["PAY_001"],
            [
                "SET_001",
                "SET_002",
            ],
            2,
        )
    )

    assert (
        result.structure_type
        == SettlementStructureType.SPLIT
    )

    assert result.relationship_count == 2


def test_multiple_payments_one_settlement_is_bundled():

    result = (
        SettlementStructureReconstructor()
        .reconstruct(
            [
                "PAY_001",
                "PAY_002",
            ],
            ["SET_001"],
            2,
        )
    )

    assert (
        result.structure_type
        == SettlementStructureType.BUNDLED
    )


def test_multiple_payments_multiple_settlements():

    result = (
        SettlementStructureReconstructor()
        .reconstruct(
            [
                "PAY_001",
                "PAY_002",
            ],
            [
                "SET_001",
                "SET_002",
            ],
            4,
        )
    )

    assert (
        result.structure_type
        == SettlementStructureType.MANY_TO_MANY
    )


def test_empty_structure_does_not_invent_records():

    result = (
        SettlementStructureReconstructor()
        .reconstruct(
            [],
            [],
            0,
        )
    )

    assert result.payment_ids == ()
    assert result.settlement_ids == ()
    assert result.relationship_count == 0


def test_input_is_not_modified():

    payments = [
        "PAY_001",
        "PAY_002",
    ]

    settlements = [
        "SET_001",
    ]

    original_payments = list(payments)
    original_settlements = list(
        settlements
    )

    (
        SettlementStructureReconstructor()
        .reconstruct(
            payments,
            settlements,
            2,
        )
    )

    assert payments == original_payments
    assert settlements == original_settlements