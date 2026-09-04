from decimal import Decimal
from datetime import datetime
from decimal import Decimal

from app.domain.enums import ScenarioType
from app.generator.registry import SCENARIO_GENERATORS
from app.domain.enums import EventType
from app.generator.scenarios import generate_partial_refund
from app.generator.generator import generate_batch
from app.generator.scenarios import (
    generate_normal_settlement,
    generate_partial_refund,
    generate_split_settlement,
)

def test_generate_batch_size():
    batch = generate_batch(
        num_cases=10,
        seed=42,
    )

    assert len(batch.cases) == 10


def test_generate_batch_is_reproducible():
    batch_1 = generate_batch(
        num_cases=10,
        seed=42,
    )

    batch_2 = generate_batch(
        num_cases=10,
        seed=42,
    )

    assert batch_1.model_dump() == batch_2.model_dump()


def test_different_seed_produces_different_data():
    batch_1 = generate_batch(
        num_cases=10,
        seed=42,
    )

    batch_2 = generate_batch(
        num_cases=10,
        seed=99,
    )

    assert batch_1.model_dump() != batch_2.model_dump()


def test_batch_financial_invariant():
    batch = generate_batch(
        num_cases=20,
        seed=42,
    )

    for case in batch.cases:
        events = list(case.event_graph.events.values())

        payment = next(
            event
            for event in events
            if event.event_type == EventType.PAYMENT_CAPTURED
        )

        refund = next(
            event
            for event in events
            if event.event_type == EventType.REFUND_CREATED
        )

        fee = next(
            event
            for event in events
            if event.event_type == EventType.FEE_APPLIED
        )

        settlements = [
            event
            for event in events
            if event.event_type == EventType.SETTLEMENT_CREATED
        ]

        assert len(settlements) in (1, 2)

        expected_total = (
            payment.amount
            - refund.amount
            - fee.amount
        )

        actual_total = sum(
            settlement.amount
            for settlement in settlements
        )

        assert actual_total == expected_total
        
def test_generate_partial_refund():
    graph = generate_partial_refund(
        case_id="CASE_REFUND",
        base_time=datetime(2026, 8, 30, 14, 0, 0),
        payment_amount=Decimal("80000.00"),
        refund_amount=Decimal("10000.00"),
        fee_amount=Decimal("1600.00"),
    )

    payment = graph.get_event("CASE_REFUND_PAYMENT_EVENT")
    refund = graph.get_event("CASE_REFUND_REFUND_EVENT")
    settlement = graph.get_event("CASE_REFUND_SETTLEMENT_EVENT")

    assert payment.amount == Decimal("80000.00")
    assert refund.amount == Decimal("10000.00")
    assert settlement.amount == Decimal("68400.00")

def test_partial_refund_rejects_full_refund():
    try:
        generate_partial_refund(
            case_id="CASE_BAD_REFUND",
            base_time=datetime(2026, 8, 30, 14, 0, 0),
            payment_amount=Decimal("50000.00"),
            refund_amount=Decimal("50000.00"),
            fee_amount=Decimal("1000.00"),
        )
    except ValueError as exc:
        assert "less than payment amount" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError for a full refund"
        )
def test_batch_contains_multiple_scenarios():
    batch = generate_batch(
        num_cases=100,
        seed=42,
    )

    scenarios = {
        case.scenario
        for case in batch.cases
    }

    assert "NORMAL_SETTLEMENT" in scenarios
    assert "PARTIAL_REFUND" in scenarios
def test_batch_scenario_counts_are_reproducible():
    batch_1 = generate_batch(
        num_cases=100,
        seed=42,
    )

    batch_2 = generate_batch(
        num_cases=100,
        seed=42,
    )

    assert batch_1.scenario_counts() == batch_2.scenario_counts()

def test_generate_split_settlement():
    graph = generate_split_settlement(
        case_id="CASE_SPLIT",
        base_time=datetime(2026, 8, 30, 16, 0, 0),
        payment_amount=Decimal("100000.00"),
        refund_amount=Decimal("0.00"),
        fee_amount=Decimal("2000.00"),
    )

    payment = graph.get_event("CASE_SPLIT_PAYMENT_EVENT")
    settlement_a = graph.get_event(
        "CASE_SPLIT_SETTLEMENT_A_EVENT"
    )
    settlement_b = graph.get_event(
        "CASE_SPLIT_SETTLEMENT_B_EVENT"
    )
    bank_a = graph.get_event(
        "CASE_SPLIT_BANK_A_EVENT"
    )
    bank_b = graph.get_event(
        "CASE_SPLIT_BANK_B_EVENT"
    )

    assert payment.amount == Decimal("100000.00")

    assert settlement_a.amount == Decimal("58800.00")
    assert settlement_b.amount == Decimal("39200.00")

    assert bank_a.amount == Decimal("58800.00")
    assert bank_b.amount == Decimal("39200.00")

    assert (
        settlement_a.amount + settlement_b.amount
        == Decimal("98000.00")
    )
def test_split_settlement_relationships():
    graph = generate_split_settlement(
        case_id="CASE_SPLIT",
        base_time=datetime(2026, 8, 30, 16, 0, 0),
        payment_amount=Decimal("100000.00"),
        refund_amount=Decimal("0.00"),
        fee_amount=Decimal("2000.00"),
    )

    payment = graph.get_event(
        "CASE_SPLIT_PAYMENT_EVENT"
    )

    settlement_a = graph.get_event(
        "CASE_SPLIT_SETTLEMENT_A_EVENT"
    )

    settlement_b = graph.get_event(
        "CASE_SPLIT_SETTLEMENT_B_EVENT"
    )

    assert (
        "CASE_SPLIT_SETTLEMENT_A_EVENT"
        in payment.related_event_ids
    )

    assert (
        "CASE_SPLIT_SETTLEMENT_B_EVENT"
        in payment.related_event_ids
    )

    assert (
        "CASE_SPLIT_BANK_A_EVENT"
        in settlement_a.related_event_ids
    )

    assert (
        "CASE_SPLIT_BANK_B_EVENT"
        in settlement_b.related_event_ids
    )
def test_all_scenarios_have_generators():
    assert (
        ScenarioType.NORMAL_SETTLEMENT
        in SCENARIO_GENERATORS
    )

    assert (
        ScenarioType.PARTIAL_REFUND
        in SCENARIO_GENERATORS
    )

    assert (
        ScenarioType.SPLIT_SETTLEMENT
        in SCENARIO_GENERATORS
    )
def test_batch_contains_split_settlements():
    batch = generate_batch(
        num_cases=100,
        seed=42,
    )

    scenarios = {
        case.scenario
        for case in batch.cases
    }

    assert "SPLIT_SETTLEMENT" in scenarios
def test_split_settlement_batch_cases_have_two_settlements():
    batch = generate_batch(
        num_cases=100,
        seed=42,
    )

    split_cases = [
        case
        for case in batch.cases
        if case.scenario == "SPLIT_SETTLEMENT"
    ]

    assert len(split_cases) > 0

    for case in split_cases:
        settlements = [
            event
            for event in case.event_graph.events.values()
            if event.event_type.value == "SETTLEMENT_CREATED"
        ]

        assert len(settlements) == 2