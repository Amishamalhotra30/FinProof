from datetime import datetime
from decimal import Decimal

from app.generator.scenarios import generate_normal_settlement
from app.generator.source_records import generate_source_records


def test_generate_source_records():
    graph = generate_normal_settlement(
        case_id="CASE_001",
        base_time=datetime(2026, 8, 30, 10, 0, 0),
    )

    records = generate_source_records(graph)

    assert len(records["orders"]) == 1
    assert len(records["payments"]) == 1
    assert len(records["refunds"]) == 1
    assert len(records["fees"]) == 1
    assert len(records["settlements"]) == 1
    assert len(records["bank"]) == 1


def test_source_records_preserve_financial_values():
    graph = generate_normal_settlement(
        case_id="CASE_001",
        base_time=datetime(2026, 8, 30, 10, 0, 0),
    )

    records = generate_source_records(graph)

    payment = records["payments"][0]
    refund = records["refunds"][0]
    fee = records["fees"][0]
    settlement = records["settlements"][0]
    bank = records["bank"][0]

    assert payment.payment_id == "CASE_001_PAYMENT"
    assert payment.amount == Decimal("50000.00")

    assert refund.amount == Decimal("5000.00")

    assert fee.amount == Decimal("1000.00")

    assert settlement.net_amount == Decimal("44000.00")

    assert bank.credit == Decimal("44000.00")
def test_variable_amounts_are_preserved_in_source_records():
    graph = generate_normal_settlement(
        case_id="CASE_VARIABLE",
        base_time=datetime(2026, 8, 30, 15, 0, 0),
        payment_amount=Decimal("75000.00"),
        refund_amount=Decimal("8000.00"),
        fee_amount=Decimal("1500.00"),
    )

    records = generate_source_records(graph)

    payment = records["payments"][0]
    settlement = records["settlements"][0]

    assert payment.amount == Decimal("75000.00")
    assert settlement.gross_amount == Decimal("75000.00")
    assert settlement.fee == Decimal("1500.00")
    assert settlement.net_amount == Decimal("65500.00")

def test_split_settlement_creates_two_settlement_records():
    from datetime import datetime
    from decimal import Decimal

    from app.generator.scenarios import generate_split_settlement

    graph = generate_split_settlement(
        case_id="CASE_SPLIT",
        base_time=datetime(2026, 8, 30, 16, 0, 0),
        payment_amount=Decimal("100000.00"),
        refund_amount=Decimal("0.00"),
        fee_amount=Decimal("2000.00"),
    )

    records = generate_source_records(graph)

    assert len(records["settlements"]) == 2
    assert len(records["bank"]) == 2

    settlement_total = sum(
        record.net_amount
        for record in records["settlements"]
    )

    bank_total = sum(
        record.credit
        for record in records["bank"]
    )

    assert settlement_total == Decimal("98000.00")
    assert bank_total == Decimal("98000.00")