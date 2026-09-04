from dataclasses import dataclass


from app.corruption.config import DEFAULT_CORRUPTION_PLAN
from app.corruption.models import CorruptionEvent
from app.corruption.planner import CorruptionPlanner
from app.domain.ground_truth import GroundTruthBatch
from app.generator.batch_records import (
    generate_batch_source_records,
)
from app.generator.generator import generate_batch


@dataclass(frozen=True)
class Benchmark:
    ground_truth: GroundTruthBatch
    clean_records: dict[str, list]
    observed_records: dict[str, list]
    corruption_events: list[CorruptionEvent]


@dataclass(frozen=True)
class BenchmarkMetrics:
    total_cases: int
    corrupted_cases: int
    detected_cases: int
    missed_cases: int
    false_positive_cases: int

    @property
    def detection_rate(self) -> float:
        if self.corrupted_cases == 0:
            return 1.0

        return (
            self.detected_cases
            / self.corrupted_cases
        )

    @property
    def precision(self) -> float:
        predicted = (
            self.detected_cases
            + self.false_positive_cases
        )

        if predicted == 0:
            return 1.0

        return (
            self.detected_cases
            / predicted
        )


def generate_benchmark(
    num_cases: int = 100,
    seed: int = 42,
) -> Benchmark:

    ground_truth = generate_batch(
        num_cases=num_cases,
        seed=seed,
    )

    clean_records = generate_batch_source_records(
        ground_truth
    )

    case_ids = [
        case.case_id
        for case in ground_truth.cases
    ]

    planner = CorruptionPlanner(
        seed=seed + 1
    )

    observed_records, corruption_events = (
        planner.apply(
            clean_records,
            case_ids,
            DEFAULT_CORRUPTION_PLAN,
        )
    )

    return Benchmark(
        ground_truth=ground_truth,
        clean_records=clean_records,
        observed_records=observed_records,
        corruption_events=corruption_events,
    )


def evaluate(
    ground_truth_case_ids: set[str],
    predicted_exception_case_ids: set[str],
    total_cases: int,
) -> BenchmarkMetrics:

    detected = (
        ground_truth_case_ids
        & predicted_exception_case_ids
    )

    false_positives = (
        predicted_exception_case_ids
        - ground_truth_case_ids
    )

    missed = (
        ground_truth_case_ids
        - predicted_exception_case_ids
    )

    return BenchmarkMetrics(
        total_cases=total_cases,
        corrupted_cases=len(
            ground_truth_case_ids
        ),
        detected_cases=len(
            detected
        ),
        missed_cases=len(
            missed
        ),
        false_positive_cases=len(
            false_positives
        ),
    )
@dataclass(frozen=True)
class CorruptionTypeMetrics:
    corruption_type: str
    injected: int
    detected: int

    @property
    def missed(self) -> int:
        return self.injected - self.detected

    @property
    def detection_rate(self) -> float:
        if self.injected == 0:
            return 1.0

        return (
            self.detected
            / self.injected
        )
def evaluate_by_corruption_type(
    corruption_events: list[CorruptionEvent],
    predicted_exception_case_ids: set[str],
) -> list[CorruptionTypeMetrics]:

    injected: dict[str, set[str]] = {}
    detected: dict[str, set[str]] = {}

    for event in corruption_events:

        corruption_type = (
            event.corruption_type.value
        )

        injected.setdefault(
            corruption_type,
            set(),
        ).add(event.case_id)

    for event in corruption_events:

        corruption_type = (
            event.corruption_type.value
        )

        if event.case_id in predicted_exception_case_ids:
            detected.setdefault(
                corruption_type,
                set(),
            ).add(event.case_id)

    metrics: list[CorruptionTypeMetrics] = []

    for corruption_type in sorted(injected):

        injected_cases = injected[
            corruption_type
        ]

        detected_cases = detected.get(
            corruption_type,
            set(),
        )

        metrics.append(
            CorruptionTypeMetrics(
                corruption_type=corruption_type,
                injected=len(injected_cases),
                detected=len(
                    injected_cases
                    & detected_cases
                ),
            )
        )

    return metrics