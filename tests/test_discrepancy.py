from decimal import Decimal

from app.verification.discrepancy import (
    DiscrepancyBuilder,
    build_discrepancy,
)
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    Materiality,
    Severity,
)


def make_failed_control() -> ControlCheck:
    return ControlCheck(
        control_id="SETTLEMENT_AMOUNT",
        control_name="Settlement amount equals expected settlement",
        status=ControlStatus.FAIL,
        expected_value=Decimal("50000.00"),
        observed_value=Decimal("49000.00"),
        difference=Decimal("-1000.00"),
        affected_event_ids=[
            "SET_001",
            "BANK_001",
        ],
        supporting_evidence_ids=[
            "EVID_001",
            "EVID_002",
        ],
        severity=Severity.HIGH,
        blocking=True,
    )


def test_failed_control_creates_discrepancy():
    discrepancy = DiscrepancyBuilder().build(
        make_failed_control()
    )

    assert discrepancy is not None
    assert (
        discrepancy.control_id
        == "SETTLEMENT_AMOUNT"
    )
    assert (
        discrepancy.expected_value
        == Decimal("50000.00")
    )
    assert (
        discrepancy.observed_value
        == Decimal("49000.00")
    )
    assert (
        discrepancy.difference
        == Decimal("-1000.00")
    )


def test_discrepancy_gets_materiality():
    discrepancy = build_discrepancy(
        make_failed_control()
    )

    assert discrepancy is not None
    assert (
        discrepancy.materiality
        == Materiality.HIGH
    )


def test_relative_difference_is_calculated():
    discrepancy = build_discrepancy(
        make_failed_control()
    )

    assert discrepancy is not None

    assert (
        discrepancy.relative_difference
        == Decimal("0.02")
    )


def test_evidence_is_preserved():
    discrepancy = build_discrepancy(
        make_failed_control()
    )

    assert discrepancy is not None

    assert discrepancy.evidence_references == [
        "EVID_001",
        "EVID_002",
    ]


def test_affected_events_are_preserved():
    discrepancy = build_discrepancy(
        make_failed_control()
    )

    assert discrepancy is not None

    assert discrepancy.affected_event_ids == [
        "SET_001",
        "BANK_001",
    ]


def test_blocking_status_is_preserved():
    discrepancy = build_discrepancy(
        make_failed_control()
    )

    assert discrepancy is not None
    assert discrepancy.blocking is True


def test_passing_control_creates_no_discrepancy():
    control = ControlCheck(
        control_id="SETTLEMENT_AMOUNT",
        control_name="Settlement amount equals expected settlement",
        status=ControlStatus.PASS,
        expected_value=Decimal("50000.00"),
        observed_value=Decimal("50000.00"),
        difference=Decimal("0"),
    )

    assert (
        DiscrepancyBuilder().build(control)
        is None
    )


def test_pending_control_creates_no_discrepancy():
    control = ControlCheck(
        control_id="BANK_CREDIT_AMOUNT",
        control_name="Bank credit equals expected bank credit",
        status=ControlStatus.PENDING,
    )

    assert (
        DiscrepancyBuilder().build(control)
        is None
    )


def test_zero_expected_value_has_no_relative_difference():
    control = ControlCheck(
        control_id="ZERO_TEST",
        control_name="Zero expected value test",
        status=ControlStatus.FAIL,
        expected_value=Decimal("0"),
        observed_value=Decimal("100"),
        difference=Decimal("100"),
    )

    discrepancy = build_discrepancy(control)

    assert discrepancy is not None
    assert (
        discrepancy.relative_difference
        is None
    )


def test_difference_can_be_derived_from_values():
    control = ControlCheck(
        control_id="DERIVED_DIFFERENCE",
        control_name="Derived difference",
        status=ControlStatus.FAIL,
        expected_value=Decimal("1000.00"),
        observed_value=Decimal("900.00"),
    )

    discrepancy = build_discrepancy(control)

    assert discrepancy is not None
    assert (
        discrepancy.difference
        == Decimal("-100.00")
    )


def test_discrepancy_is_uninvestigated():
    discrepancy = build_discrepancy(
        make_failed_control()
    )

    assert discrepancy is not None

    assert (
        discrepancy.investigation_status.value
        == "UNINVESTIGATED"
    )