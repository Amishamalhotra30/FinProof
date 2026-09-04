from decimal import Decimal

from app.reconciliation.metrics import (
    ReconciliationMetricsCalculator,
    ReconciliationTimer,
)
from app.reconciliation.models import (
    Cardinality,
    MatchMethod,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)


def make_relationship(
    relationship_id,
    status=RelationshipStatus.CONFIRMED,
    method=MatchMethod.EXACT_ID,
):

    return Relationship(
        relationship_id=relationship_id,
        source_record_id="PAY_001",
        target_record_id=relationship_id,
        relationship_type=(
            RelationshipType
            .SETTLEMENT_FOR_PAYMENT
        ),
        cardinality=Cardinality.ONE_TO_ONE,
        method=method,
        evidence=["test evidence"],
        status=status,
        created_at=__import__(
            "datetime"
        ).datetime.now(),
    )


def test_empty_metrics():

    result = (
        ReconciliationMetricsCalculator
        .calculate(
            [],
            Decimal("100"),
        )
    )

    assert result.relationships_processed == 0
    assert result.confirmed_relationships == 0
    assert result.ambiguous_relationships == 0
    assert result.unresolved_relationships == 0
    assert result.ai_assisted_relationships == 0

    assert result.ambiguity_rate == Decimal("0")
    assert result.ai_assisted_rate == Decimal("0")


def test_relationship_status_counts():

    relationships = [
        make_relationship("R1"),
        make_relationship("R2"),
        make_relationship(
            "R3",
            RelationshipStatus.AMBIGUOUS,
        ),
        make_relationship(
            "R4",
            RelationshipStatus.UNRESOLVED,
        ),
    ]

    result = (
        ReconciliationMetricsCalculator
        .calculate(
            relationships,
            Decimal("1000"),
        )
    )

    assert result.relationships_processed == 4
    assert result.confirmed_relationships == 2
    assert result.ambiguous_relationships == 1
    assert result.unresolved_relationships == 1


def test_ambiguity_rate():

    relationships = [
        make_relationship("R1"),
        make_relationship("R2"),
        make_relationship(
            "R3",
            RelationshipStatus.AMBIGUOUS,
        ),
        make_relationship(
            "R4",
            RelationshipStatus.AMBIGUOUS,
        ),
    ]

    result = (
        ReconciliationMetricsCalculator
        .calculate(
            relationships,
            Decimal("1000"),
        )
    )

    assert result.ambiguity_rate == Decimal(
        "0.5"
    )


def test_ai_assisted_rate():

    relationships = [
        make_relationship("R1"),
        make_relationship(
            "R2",
            method=MatchMethod.AI_ASSISTED,
        ),
        make_relationship(
            "R3",
            method=MatchMethod.AI_ASSISTED,
        ),
        make_relationship("R4"),
    ]

    result = (
        ReconciliationMetricsCalculator
        .calculate(
            relationships,
            Decimal("1000"),
        )
    )

    assert result.ai_assisted_rate == Decimal(
        "0.5"
    )


def test_throughput():

    result = (
        ReconciliationMetricsCalculator
        .calculate(
            [
                make_relationship("R1"),
                make_relationship("R2"),
            ],
            Decimal("1000"),
        )
    )

    assert result.throughput == Decimal("2")


def test_precision():

    predicted = {
        "R1",
        "R2",
        "R3",
    }

    ground_truth = {
        "R1",
        "R2",
        "R4",
    }

    result = (
        ReconciliationMetricsCalculator
        .evaluate_precision(
            predicted,
            ground_truth,
        )
    )

    assert result == Decimal(
        "0.6666666666666666666666666667"
    )


def test_recall():

    predicted = {
        "R1",
        "R2",
    }

    ground_truth = {
        "R1",
        "R2",
        "R3",
        "R4",
    }

    result = (
        ReconciliationMetricsCalculator
        .evaluate_recall(
            predicted,
            ground_truth,
        )
    )

    assert result == Decimal("0.5")


def test_precision_with_no_predictions():

    result = (
        ReconciliationMetricsCalculator
        .evaluate_precision(
            set(),
            {"R1"},
        )
    )

    assert result == Decimal("0")


def test_recall_with_no_ground_truth():

    result = (
        ReconciliationMetricsCalculator
        .evaluate_recall(
            {"R1"},
            set(),
        )
    )

    assert result == Decimal("0")


def test_evaluation_is_attached_without_changing_runtime_metrics():

    metrics = (
        ReconciliationMetricsCalculator
        .calculate(
            [
                make_relationship("R1"),
            ],
            Decimal("500"),
        )
    )

    evaluated = (
        ReconciliationMetricsCalculator
        .with_evaluation(
            metrics,
            {"R1"},
            {"R1", "R2"},
        )
    )

    assert evaluated.relationship_precision == (
        Decimal("1")
    )

    assert evaluated.relationship_recall == (
        Decimal("0.5")
    )

    assert evaluated.relationships_processed == (
        metrics.relationships_processed
    )

    assert evaluated.processing_time_ms == (
        metrics.processing_time_ms
    )


def test_metrics_do_not_require_ground_truth():

    result = (
        ReconciliationMetricsCalculator
        .calculate(
            [
                make_relationship("R1"),
            ],
            Decimal("250"),
        )
    )

    assert result.relationship_precision is None
    assert result.relationship_recall is None


def test_timer_requires_start():

    timer = ReconciliationTimer()

    try:
        timer.elapsed_ms()
        raise AssertionError(
            "Timer should require start"
        )
    except RuntimeError:
        pass


def test_timer_measures_elapsed_time():

    timer = ReconciliationTimer()

    timer.start()

    elapsed = timer.elapsed_ms()

    assert elapsed >= Decimal("0")