from __future__ import annotations

from decimal import Decimal

from app.evaluation.report import Phase8Report
from app.verification.benchmark import evaluate_phase5


class Phase8EvaluationOrchestrator:
    """
    Independent Phase 8 evaluation orchestrator.

    Existing phase evaluators remain the source of truth for
    their respective metrics.

    This layer only coordinates and consolidates their results.
    """

    def run(
        self,
        num_cases: int = 100,
        seed: int = 42,
        *,
        verification_evaluation=None,
        investigation_evaluation=None,
        decision_evaluation=None,
    ) -> Phase8Report:
        """
        Build a consolidated Phase 8 report.

        Optional evaluation objects allow existing phase runners
        to supply their already-computed results.

        When verification_evaluation is omitted, Phase 5 is
        evaluated using the existing independent benchmark.
        """

        if verification_evaluation is None:
            verification_evaluation = evaluate_phase5(
                num_cases=num_cases,
                seed=seed,
            )

        investigation = investigation_evaluation
        decision = decision_evaluation

        return self._build_report(
            num_cases=num_cases,
            verification=verification_evaluation,
            investigation=investigation,
            decision=decision,
        )

    @staticmethod
    def _build_report(
        *,
        num_cases: int,
        verification,
        investigation,
        decision,
    ) -> Phase8Report:
        # ------------------------------------------------------
        # Investigation defaults
        #
        # Investigation is optional because Phase 6 currently
        # has its own benchmark runner.
        # ------------------------------------------------------

        if investigation is None:
            investigation_cases = 0

            investigation_coverage = Decimal("0")
            investigation_full_rate = Decimal("0")
            investigation_false_rate = Decimal("0")
            investigation_explanation_coverage = Decimal("0")

            investigation_time = Decimal("0")
            investigation_throughput = Decimal("0")

        else:
            investigation_cases = (
                investigation.total_cases
            )

            investigation_coverage = (
                investigation.investigation_coverage
            )

            investigation_full_rate = (
                investigation.full_explanation_rate
            )

            investigation_false_rate = (
                investigation.false_explanation_rate
            )

            investigation_explanation_coverage = (
                investigation.explanation_coverage
            )

            investigation_time = (
                investigation.processing_time_ms
            )

            investigation_throughput = (
                investigation.throughput
            )

        # ------------------------------------------------------
        # Decision defaults
        # ------------------------------------------------------

        if decision is None:
            decision_cases = 0

            decision_automation_rate = Decimal("0")
            decision_human_review_rate = Decimal("0")
            decision_false_resolution_rate = Decimal("0")

            decision_time = Decimal("0")
            decision_throughput = Decimal("0")

        else:
            decision_cases = decision.total_cases

            decision_automation_rate = (
                Decimal(str(decision.automation_rate))
            )

            decision_human_review_rate = (
                Decimal(str(decision.human_review_rate))
            )

            decision_false_resolution_rate = (
                Decimal(
                    str(
                        decision.false_resolution_rate
                    )
                )
            )

            decision_time = (
                decision.processing_time_ms
            )

            decision_throughput = (
                decision.throughput
            )

        return Phase8Report(
            benchmark_cases=num_cases,

            verification_cases=(
                verification.total_cases
            ),
            investigation_cases=investigation_cases,
            decision_cases=decision_cases,

            verification_false_pass_rate=(
                verification.false_pass_rate
            ),
            verification_false_fail_rate=(
                verification.false_fail_rate
            ),
            verification_material_detection_rate=(
                verification.material_failure_detection_rate
            ),
            verification_discrepancy_coverage=(
                verification.financial_discrepancy_coverage
            ),

            investigation_coverage=(
                investigation_coverage
            ),
            investigation_full_explanation_rate=(
                investigation_full_rate
            ),
            investigation_false_explanation_rate=(
                investigation_false_rate
            ),
            investigation_explanation_coverage=(
                investigation_explanation_coverage
            ),

            decision_automation_rate=(
                decision_automation_rate
            ),
            decision_human_review_rate=(
                decision_human_review_rate
            ),
            decision_false_resolution_rate=(
                decision_false_resolution_rate
            ),

            verification_processing_time_ms=(
                verification.processing_time_ms
            ),
            investigation_processing_time_ms=(
                investigation_time
            ),
            decision_processing_time_ms=(
                decision_time
            ),

            verification_throughput=(
                verification.verification_throughput
            ),
            investigation_throughput=(
                investigation_throughput
            ),
            decision_throughput=(
                decision_throughput
            ),
        )


def run_phase8_evaluation(
    num_cases: int = 100,
    seed: int = 42,
    *,
    verification_evaluation=None,
    investigation_evaluation=None,
    decision_evaluation=None,
) -> Phase8Report:
    return Phase8EvaluationOrchestrator().run(
        num_cases=num_cases,
        seed=seed,
        verification_evaluation=(
            verification_evaluation
        ),
        investigation_evaluation=(
            investigation_evaluation
        ),
        decision_evaluation=decision_evaluation,
    )