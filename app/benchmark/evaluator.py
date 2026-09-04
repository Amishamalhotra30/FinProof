from dataclasses import dataclass


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