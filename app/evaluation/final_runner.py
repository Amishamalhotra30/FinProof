from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from types import ModuleType

from app.decisions.metrics import (
    DecisionMetricsCalculator,
)
from app.decisions.models import (
    DecisionOutcome,
    DecisionResult,
)
from app.decisions.policy import DecisionPolicy
from app.decisions.service import DecisionService

from app.evaluation.adversarial import (
    AdversarialCaseResult,
    run_standard_adversarial_suite,
)

from app.evaluation.failure_analysis import (
    FailureAnalyzer,
    FailureCategory,
    FailureRecord,
    FailureType,
)

from app.evaluation.performance import (
    PerformanceBenchmark,
    measure_performance,
)


@dataclass(frozen=True)
class FinalPhase8Report:
    """
    Unified evaluation-only Phase 8 report.

    Phase 5, Phase 6 and Phase 7 retain their existing
    phase-specific benchmark datasets.

    Therefore this report aggregates phase-level evaluation
    results without claiming same-case end-to-end accuracy.
    """

    verification: object
    investigation: object
    decision: object

    adversarial_results: tuple[
        AdversarialCaseResult,
        ...
    ]

    performance: PerformanceBenchmark
    failure_analysis: object

    @property
    def adversarial_total(self) -> int:
        return len(
            self.adversarial_results
        )

    @property
    def adversarial_safe(self) -> int:
        return sum(
            1
            for result in self.adversarial_results
            if result.safe
        )

    @property
    def adversarial_safety_rate(self) -> Decimal:
        if self.adversarial_total == 0:
            return Decimal("0")

        return (
            Decimal(
                str(self.adversarial_safe)
            )
            / Decimal(
                str(self.adversarial_total)
            )
        )

    @property
    def safety_status(self) -> str:
        """
        Overall Phase 8 safety verdict.

        Any false pass, false explanation, false resolution,
        or unsafe adversarial behavior requires review.
        """

        if (
            self.verification.false_pass_rate > 0
            or (
                self.investigation
                .false_explanation_rate
                > 0
            )
            or (
                self.decision
                .false_resolution_rate
                > 0
            )
            or (
                self.adversarial_safe
                < self.adversarial_total
            )
        ):
            return "REVIEW_REQUIRED"

        return "SAFE"


class Phase8FinalRunner:
    """
    Unified evaluation-only Phase 8 runner.

    This layer coordinates the existing phase evaluators.

    Hidden benchmark ground truth remains outside the
    production financial-control pipeline.
    """

    def run(
        self,
        num_cases: int = 100,
        seed: int = 42,
    ) -> FinalPhase8Report:

# =====================================================
# PHASE 5 — VERIFICATION
# =====================================================

        phase5_module = self._load_script_module(
        "run_phase5_evaluation.py"
    )

        evaluate_phase5 = getattr(
        phase5_module,
        "run_phase5_evaluation",
    )

        verification = evaluate_phase5(
            num_cases=num_cases,
            seed=seed,
    )

        # =====================================================
        # PHASE 6 — INVESTIGATION
        # =====================================================

        phase6_module = self._load_script_module(
            "run_phase6_evaluation.py"
        )

        evaluate_phase6 = getattr(
            phase6_module,
            "evaluate_phase6",
        )

        investigation = evaluate_phase6(
            num_cases=num_cases,
            seed=seed,
        )

        # =====================================================
        # PHASE 7 — DECISION
        # =====================================================

        decision = self._evaluate_phase7()

        # =====================================================
        # PHASE 8 — ADVERSARIAL SAFETY
        # =====================================================

        adversarial_results = tuple(
            run_standard_adversarial_suite()
        )

        # =====================================================
        # PHASE 8 — PERFORMANCE
        # =====================================================

        performance = measure_performance(
            case_counts=(
                100,
                1_000,
                5_000,
                10_000,
            ),
            seed=seed,
        )

        # =====================================================
        # PHASE 8 — FAILURE ANALYSIS
        # =====================================================

        failure_analysis = (
            self._build_failure_analysis(
                verification=verification,
                investigation=investigation,
                decision=decision,
                adversarial_results=(
                    adversarial_results
                ),
            )
        )

        return FinalPhase8Report(
            verification=verification,
            investigation=investigation,
            decision=decision,
            adversarial_results=(
                adversarial_results
            ),
            performance=performance,
            failure_analysis=failure_analysis,
        )

    # =========================================================
    # SCRIPT LOADING
    # =========================================================

    @staticmethod
    def _load_script_module(
        filename: str,
    ) -> ModuleType:
        """
        Load an evaluation script directly from the project's
        scripts directory.

        This avoids depending on `scripts` being an installed
        Python package or namespace package.

        Only evaluation scripts are loaded here.
        """

        project_root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        script_path = (
            project_root
            / "scripts"
            / filename
        )

        if not script_path.exists():
            raise FileNotFoundError(
                "Evaluation script not found: "
                f"{script_path}"
            )

        module_name = (
            f"_finproof_phase8_{script_path.stem}"
        )

        spec = (
            importlib.util
            .spec_from_file_location(
                module_name,
                script_path,
            )
        )

        if spec is None:
            raise ImportError(
                "Could not create module specification "
                f"for {script_path}"
            )

        if spec.loader is None:
            raise ImportError(
                "Could not load evaluation script "
                f"{script_path}"
            )

        module = (
            importlib.util
            .module_from_spec(spec)
        )

        spec.loader.exec_module(module)

        return module

    # =========================================================
    # PHASE 7
    # =========================================================

    @classmethod
    def _evaluate_phase7(cls):
        """
        Reuse Phase 7's actual benchmark cases and policy.

        We intentionally do NOT call Phase 7's
        print-oriented `run_evaluation()` function because
        that function returns None.

        Instead we reuse its benchmark-case construction and
        evaluate those cases here.
        """

        phase7_module = cls._load_script_module(
            "run_phase7_evaluation.py"
        )

        build_benchmark_cases = getattr(
            phase7_module,
            "_build_benchmark_cases",
        )

        benchmark_cases = (
            build_benchmark_cases()
        )

        policy = DecisionPolicy(
            auto_resolution_threshold=Decimal(
                "1000"
            )
        )

        service = DecisionService(
            policy=policy
        )

        decisions: list[
            DecisionResult
        ] = []

        ground_truth: dict[
            str,
            DecisionOutcome,
        ] = {}

        started = perf_counter()

        for (
            verification,
            investigation,
            expected,
        ) in benchmark_cases:

            service_result = service.decide(
                verification,
                investigation,
            )

            # -------------------------------------------------
            # IMPORTANT
            #
            # DecisionService.decide() returns:
            #
            #     DecisionServiceResult
            #
            # Its `.decision` field contains:
            #
            #     DecisionResult
            #
            # DecisionMetricsCalculator expects a list of
            # DecisionResult objects.
            # -------------------------------------------------

            decisions.append(
                service_result.decision
            )

            ground_truth[
                verification.case_id
            ] = expected

        elapsed_ms = Decimal(
            str(
                (
                    perf_counter()
                    - started
                )
                * 1000
            )
        )

        return (
            DecisionMetricsCalculator()
            .calculate(
                decisions,
                ground_truth=ground_truth,
                processing_time_ms=elapsed_ms,
            )
        )

    # =========================================================
    # FAILURE ANALYSIS
    # =========================================================

    @staticmethod
    def _build_failure_analysis(
        *,
        verification,
        investigation,
        decision,
        adversarial_results,
    ):
        """
        Convert observed cross-phase safety failures into
        the existing Phase 8 failure-analysis model.
        """

        failures: list[
            FailureRecord
        ] = []

        # -----------------------------------------------------
        # VERIFICATION
        # -----------------------------------------------------

        if verification.false_pass_rate > 0:
            failures.append(
                FailureRecord(
                    case_id="PHASE5",
                    category=(
                        FailureCategory
                        .VERIFICATION
                    ),
                    failure_type=(
                        FailureType
                        .FALSE_PASS
                    ),
                    financial_value=(
                        Decimal("0")
                    ),
                    description=(
                        "Verification produced "
                        "one or more false passes."
                    ),
                )
            )

        if verification.false_fail_rate > 0:
            failures.append(
                FailureRecord(
                    case_id="PHASE5",
                    category=(
                        FailureCategory
                        .VERIFICATION
                    ),
                    failure_type=(
                        FailureType
                        .FALSE_FAIL
                    ),
                    financial_value=(
                        Decimal("0")
                    ),
                    description=(
                        "Verification produced "
                        "one or more false fails."
                    ),
                )
            )

        # -----------------------------------------------------
        # INVESTIGATION
        # -----------------------------------------------------

        if (
            investigation
            .false_explanation_rate
            > 0
        ):
            failures.append(
                FailureRecord(
                    case_id="PHASE6",
                    category=(
                        FailureCategory
                        .INVESTIGATION
                    ),
                    failure_type=(
                        FailureType
                        .FALSE_EXPLANATION
                    ),
                    financial_value=(
                        Decimal("0")
                    ),
                    description=(
                        "Investigation produced "
                        "one or more false explanations."
                    ),
                )
            )

        # -----------------------------------------------------
        # DECISION
        # -----------------------------------------------------

        if (
            decision
            .false_resolution_rate
            > 0
        ):
            failures.append(
                FailureRecord(
                    case_id="PHASE7",
                    category=(
                        FailureCategory
                        .DECISION
                    ),
                    failure_type=(
                        FailureType
                        .FALSE_RESOLUTION
                    ),
                    financial_value=(
                        Decimal("0")
                    ),
                    description=(
                        "Decision layer produced "
                        "one or more false resolutions."
                    ),
                )
            )

        # -----------------------------------------------------
        # ADVERSARIAL SAFETY
        # -----------------------------------------------------

        for result in (
            adversarial_results
        ):

            if result.safe:
                continue

            failures.append(
                FailureRecord(
                    case_id=result.case_id,
                    category=(
                        FailureCategory
                        .SAFETY
                    ),
                    failure_type=(
                        FailureType
                        .SAFE_DEGRADATION_FAILURE
                    ),
                    financial_value=(
                        result.explained_amount
                    ),
                    description=(
                        f"Adversarial scenario "
                        f"{result.scenario} was unsafe."
                    ),
                )
            )

        return FailureAnalyzer().analyze(
            failures
        )


def run_phase8_final(
    num_cases: int = 100,
    seed: int = 42,
) -> FinalPhase8Report:
    """
    Convenience entry point for the unified Phase 8
    evaluation runner.
    """

    return Phase8FinalRunner().run(
        num_cases=num_cases,
        seed=seed,
    )