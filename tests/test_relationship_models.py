from datetime import datetime

from app.reconciliation.models import (
    Cardinality,
    MatchMethod,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)


def test_relationship_model():

    relationship = Relationship(
        relationship_id="REL_001",
        source_record_id="PAY_001",
        target_record_id="SET_001",
        relationship_type=(
            RelationshipType.SETTLEMENT_FOR_PAYMENT
        ),
        cardinality=Cardinality.ONE_TO_ONE,
        method=MatchMethod.EXACT_ID,
        evidence=[
            "payment_id",
            "settlement_payment_ref",
        ],
        status=RelationshipStatus.CONFIRMED,
        created_at=datetime(
            2026,
            8,
            31,
            12,
            0,
        ),
    )

    assert (
        relationship.relationship_id
        == "REL_001"
    )

    assert (
        relationship.relationship_type
        == RelationshipType.SETTLEMENT_FOR_PAYMENT
    )

    assert (
        relationship.cardinality
        == Cardinality.ONE_TO_ONE
    )

    assert (
        relationship.method
        == MatchMethod.EXACT_ID
    )

    assert (
        relationship.status
        == RelationshipStatus.CONFIRMED
    )


def test_relationship_supports_one_to_many():

    relationship = Relationship(
        relationship_id="REL_002",
        source_record_id="PAY_001",
        target_record_id="SET_001",
        relationship_type=(
            RelationshipType.SETTLEMENT_FOR_PAYMENT
        ),
        cardinality=Cardinality.ONE_TO_MANY,
        method=MatchMethod.EXACT_ID,
        evidence=[
            "payment_id"
        ],
        status=RelationshipStatus.CONFIRMED,
        created_at=datetime.now(),
    )

    assert (
        relationship.cardinality
        == Cardinality.ONE_TO_MANY
    )


def test_ambiguous_relationship_is_supported():

    relationship = Relationship(
        relationship_id="REL_003",
        source_record_id="BANK_001",
        target_record_id="SET_001",
        relationship_type=(
            RelationshipType.BANK_FOR_SETTLEMENT
        ),
        cardinality=Cardinality.ONE_TO_ONE,
        method=MatchMethod.AMOUNT_TIME_MATCH,
        evidence=[
            "same_amount",
            "timestamp_within_window",
        ],
        status=RelationshipStatus.AMBIGUOUS,
        created_at=datetime.now(),
    )

    assert (
        relationship.status
        == RelationshipStatus.AMBIGUOUS
    )

    assert (
        "same_amount"
        in relationship.evidence
    )