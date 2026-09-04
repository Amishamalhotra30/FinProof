from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter

from app.evaluation.dataset import (
    EvaluationDataset,
)
from app.evaluation.ground_truth import (
    EvaluationGroundTruth,
)
from app.evaluation.models import (
    CaseEvaluation,
    EvaluationSplit,
    EvaluationSummary,
)


@dataclass(frozen=True)
class EvaluationRun:
    """
    Complete result of one Phase 8 evaluation run.
    """

    cases: tuple[CaseEvaluation, ...]
    summaries: tuple[EvaluationSummary, ...]

    @property
    def total_cases(self) -> int:
        return len(self.cases)

    def summary_for(
        self,
        split: EvaluationSplit,
    ) -> EvaluationSummary | None:
        for summary in self.summaries:
            if summary.split == split:
                return summary

        return None


class EvaluationRunner:
    """
    Independent Phase 8 evaluation harness.

    The runner compares already-produced application
    results against hidden ground truth.

    It does not modify application results.
    """

    def evaluate(
        self,
        dataset: EvaluationDataset,
        ground_truth: EvaluationGroundTruth,
        actual_results: dict[str, object],
    ) -> EvaluationRun:
        start = perf_counter()

        truth_by_case = ground_truth.by_case_id()

        evaluations: list[CaseEvaluation] = []

        for case in dataset.cases:
            truth = truth_by_case.get(case.case_id)

            if truth is None:
                continue

            actual = actual_results.get(case.case_id)

            if actual is None:
                continue

            evaluation = self._evaluate_case(
                truth=truth,
                actual=actual,
            )

            evaluations.append(evaluation)

        elapsed_ms = Decimal(
            str(
                (perf_counter() - start)
                * 1000
            )
        )

        summaries = []

        for split in EvaluationSplit:
            split_evaluations = [
                evaluation
                for evaluation in evaluations
                if self._case_split(
                    dataset,
                    evaluation.case_id,
                )
                == split
            ]

            total_for_split = len(
                dataset.cases_for_split(split)
            )

            summaries.append(
                self._build_summary(
                    split=split,
                    total_cases=total_for_split,
                    evaluations=split_evaluations,
                    processing_time_ms=elapsed_ms,
                )
            )

        return EvaluationRun(
            cases=tuple(evaluations),
            summaries=tuple(summaries),
        )

    @staticmethod
    def _evaluate_case(
        truth,
        actual,
    ) -> CaseEvaluation:
        actual_failure = (
            EvaluationRunner._actual_failure(
                actual
            )
        )

        actual_decision = (
            EvaluationRunner._actual_decision(
                actual
            )
        )

        return CaseEvaluation(
            case_id=truth.case_id,
            expected_failure=truth.expected_failure,
            detected_failure=actual_failure,
            expected_material_failure=(
                truth.expected_material_failure
            ),
            detected_material_failure=(
                EvaluationRunner._actual_material_failure(
                    actual
                )
            ),
            expected_decision=(
                truth.expected_decision
            ),
            actual_decision=actual_decision,
            financial_impact=abs(
                truth.financial_impact
            ),
        )

    @staticmethod
    def _actual_failure(
        result,
    ) -> bool:
        status = getattr(
            result,
            "status",
            None,
        )

        if hasattr(status, "value"):
            status = status.value

        if status == "FAILED":
            return True

        discrepancies = getattr(
            result,
            "discrepancies",
            None,
        )

        return bool(discrepancies)

    @staticmethod
    def _actual_material_failure(
        result,
    ) -> bool:
        discrepancies = getattr(
            result,
            "discrepancies",
            [],
        )

        for discrepancy in discrepancies:
            materiality = getattr(
                discrepancy,
                "materiality",
                None,
            )

            if hasattr(materiality, "value"):
                materiality = materiality.value

            if materiality in {
                "MEDIUM",
                "HIGH",
            }:
                return True

        return False

    @staticmethod
    def _actual_decision(
        result,
    ) -> str | None:
        decision = getattr(
            result,
            "decision",
            None,
        )

        if hasattr(decision, "value"):
            return decision.value

        if decision is None:
            return None

        return str(decision)

    @staticmethod
    def _case_split(
        dataset: EvaluationDataset,
        case_id: str,
    ) -> EvaluationSplit:
        for case in dataset.cases:
            if case.case_id == case_id:
                return case.split

        raise KeyError(
            f"Unknown evaluation case: {case_id}"
        )

    @staticmethod
    def _build_summary(
        split: EvaluationSplit,
        total_cases: int,
        evaluations: list[CaseEvaluation],
        processing_time_ms: Decimal,
    ) -> EvaluationSummary:
        expected_failures = sum(
            evaluation.expected_failure
            for evaluation in evaluations
        )

        detected_failures = sum(
            evaluation.detected_failure
            for evaluation in evaluations
        )

        false_passes = sum(
            evaluation.expected_failure
            and not evaluation.detected_failure
            for evaluation in evaluations
        )

        false_fails = sum(
            not evaluation.expected_failure
            and evaluation.detected_failure
            for evaluation in evaluations
        )

        decision_matches = sum(
            evaluation.decision_correct
            for evaluation in evaluations
        )

        decision_mismatches = (
            len(evaluations)
            - decision_matches
        )

        total_financial_impact = sum(
            (
                evaluation.financial_impact
                for evaluation in evaluations
            ),
            Decimal("0"),
        )

        return EvaluationSummary(
            split=split,
            total_cases=total_cases,
            evaluated_cases=len(evaluations),
            skipped_cases=(
                total_cases
                - len(evaluations)
            ),
            expected_failures=expected_failures,
            detected_failures=detected_failures,
            false_passes=false_passes,
            false_fails=false_fails,
            decision_matches=decision_matches,
            decision_mismatches=(
                decision_mismatches
            ),
            total_financial_impact=(
                total_financial_impact
            ),
            processing_time_ms=(
                processing_time_ms
            ),
        )