from __future__ import annotations

from dataclasses import dataclass

from app.decisions.actions import (
    DecisionActionExecutor,
    OperationalAction,
)
from app.decisions.audit import AuditLog
from app.decisions.evaluator import DecisionEvaluator
from app.decisions.models import (
    CaseState,
    CaseWorkflow,
    DecisionOutcome,
    DecisionPolicy,
    DecisionResult,
    HumanReviewPackage,
    HumanReviewRecord,
    ReviewAction,
)
from app.decisions.state_machine import (
    DecisionStateMachine,
)
from app.investigation.models import InvestigationResult
from app.verification.models import VerificationResult


@dataclass(frozen=True)
class DecisionServiceResult:
    """
    Complete operational output of one Phase 7 case decision.

    This is an orchestration result. It contains the deterministic
    decision, resulting workflow state, bounded operational action,
    and audit entry.
    """

    decision: DecisionResult
    workflow: CaseWorkflow
    action: OperationalAction
    audit_entry_id: str


class DecisionService:
    """
    Application service coordinating the Phase 7 decision flow.

    Responsibilities:

        Phase 5 verification
                ↓
        optional Phase 6 investigation
                ↓
        DecisionEvaluator
                ↓
        DecisionResult
                ↓
        StateMachine
                ↓
        Bounded Action
                ↓
        AuditLog

    This service does not:
        - perform financial mutations
        - retrieve investigation evidence
        - invent financial events
        - make independent policy decisions
        - call an LLM
    """

    def __init__(
        self,
        policy: DecisionPolicy | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self.evaluator = DecisionEvaluator(
            policy=policy
        )

        self.action_executor = (
            DecisionActionExecutor()
        )

        self.audit_log = (
            audit_log
            if audit_log is not None
            else AuditLog()
        )

        self._workflows: dict[
            str,
            CaseWorkflow,
        ] = {}

        self._machines: dict[
            str,
            DecisionStateMachine,
        ] = {}

        # Keep the complete DecisionResult available for
        # subsequent human-review operations.
        #
        # CaseWorkflow intentionally stores only the current
        # DecisionOutcome, while actions and audit operations
        # require the complete DecisionResult.
        self._decision_results: dict[
            str,
            DecisionResult,
        ] = {}

    # ========================================================
    # CASE DECISION
    # ========================================================

    def decide(
        self,
        verification: VerificationResult,
        investigation: InvestigationResult | None = None,
    ) -> DecisionServiceResult:
        """
        Evaluate and operationalize one Phase 7 case.
        """

        case_id = verification.case_id

        self._validate_investigation(
            verification,
            investigation,
        )

        machine = self._get_or_create_machine(
            case_id
        )

        self._prepare_for_decision(
            machine,
            investigation,
        )

        decision = self.evaluator.evaluate(
            verification,
            investigation,
        )

        # Retain the complete decision artifact for later
        # review/package/audit operations.
        self._decision_results[case_id] = decision

        machine.apply_decision(
            decision.decision
        )

        action = self.action_executor.execute(
            decision
        )

        audit_entry = self.audit_log.record_decision(
            decision,
            verification_status=(
                verification.status.value
            ),
            investigation_status=(
                investigation.status.value
                if investigation is not None
                else None
            ),
        )

        workflow = self._build_workflow(
            case_id=case_id,
            machine=machine,
            decision=decision,
        )

        self._workflows[case_id] = workflow

        return DecisionServiceResult(
            decision=decision,
            workflow=workflow,
            action=action,
            audit_entry_id=audit_entry.audit_id,
        )

    # ========================================================
    # HUMAN REVIEW
    # ========================================================

    def review(
        self,
        case_id: str,
        action: ReviewAction,
        comment: str,
        *,
        reviewer_id: str | None = None,
        verification_status: str = "FAILED",
        investigation_status: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> HumanReviewRecord:
        """
        Record and apply one human review action.

        The state machine remains the authority on whether the
        action is legally allowed for the current workflow state.
        """

        machine = self._require_machine(
            case_id
        )

        workflow = self._workflows.get(
            case_id
        )

        if workflow is None or workflow.decision is None:
            raise ValueError(
                f"No decision exists for case "
                f"{case_id}."
            )

        # CaseWorkflow stores DecisionOutcome only.
        # Actions require the complete DecisionResult.
        decision = self._decision_results.get(
            case_id
        )

        if decision is None:
            raise ValueError(
                f"No decision result exists for case "
                f"{case_id}."
            )

        review_record = (
            self.action_executor.record_review(
                decision,
                action,
                comment,
                reviewer_id=reviewer_id,
            )
        )

        machine.apply_review_action(
            action
        )

        self.audit_log.record_human_review(
            review_record,
            verification_status=verification_status,
            investigation_status=investigation_status,
            evidence_ids=evidence_ids,
            policy_rule_id=(
                decision.policy_rule_id
            ),
        )

        updated_workflow = self._build_workflow(
            case_id=case_id,
            machine=machine,
            decision=decision,
            review_record=review_record,
        )

        self._workflows[case_id] = (
            updated_workflow
        )

        return review_record

    # ========================================================
    # REVIEW PACKAGE
    # ========================================================

    def get_review_package(
        self,
        case_id: str,
        *,
        discrepancy_id: str | None = None,
        control_id: str | None = None,
        investigation_status: str | None = None,
        investigation_summary: str | None = None,
        investigation_conclusion: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> HumanReviewPackage:
        """
        Build the bounded review package for a case.
        """

        workflow = self._workflows.get(
            case_id
        )

        if workflow is None or workflow.decision is None:
            raise ValueError(
                f"No decision exists for case "
                f"{case_id}."
            )

        # CaseWorkflow stores only DecisionOutcome.
        # Review-package construction requires DecisionResult.
        decision = self._decision_results.get(
            case_id
        )

        if decision is None:
            raise ValueError(
                f"No decision result exists for case "
                f"{case_id}."
            )

        return (
            self.action_executor
            .create_review_package(
                decision,
                discrepancy_id=discrepancy_id,
                control_id=control_id,
                investigation_status=(
                    investigation_status
                ),
                investigation_summary=(
                    investigation_summary
                ),
                investigation_conclusion=(
                    investigation_conclusion
                ),
                evidence_ids=evidence_ids,
            )
        )

    # ========================================================
    # WORKFLOW ACCESS
    # ========================================================

    def get_workflow(
        self,
        case_id: str,
    ) -> CaseWorkflow | None:
        """
        Return the current workflow record for a case.
        """

        return self._workflows.get(
            case_id
        )

    def get_state(
        self,
        case_id: str,
    ) -> CaseState:
        """
        Return the current state for a case.
        """

        return self._require_machine(
            case_id
        ).state

    def get_audit_history(
        self,
        case_id: str,
    ):
        """
        Return complete append-only audit history.
        """

        return self.audit_log.get_case_history(
            case_id
        )

    # ========================================================
    # REINVESTIGATION
    # ========================================================

    def request_reinvestigation(
        self,
        case_id: str,
    ) -> CaseState:
        """
        Move a rejected/evidence-requested case into
        the explicit reinvestigation state.
        """

        machine = self._require_machine(
            case_id
        )

        machine.reinvestigate()

        workflow = self._workflows.get(
            case_id
        )

        if workflow is not None:
            decision = self._decision_results.get(
                case_id
            )

            self._workflows[case_id] = (
                self._build_workflow(
                    case_id=case_id,
                    machine=machine,
                    decision=decision,
                )
            )

        return machine.state

    def start_reinvestigation(
        self,
        case_id: str,
    ) -> CaseState:
        """
        Move a REINVESTIGATION state into INVESTIGATION.
        """

        machine = self._require_machine(
            case_id
        )

        machine.start_investigation()

        workflow = self._workflows.get(
            case_id
        )

        if workflow is not None:
            decision = self._decision_results.get(
                case_id
            )

            self._workflows[case_id] = (
                self._build_workflow(
                    case_id=case_id,
                    machine=machine,
                    decision=decision,
                )
            )

        return machine.state

    # ========================================================
    # INTERNAL STATE MANAGEMENT
    # ========================================================

    def _get_or_create_machine(
        self,
        case_id: str,
    ) -> DecisionStateMachine:
        machine = self._machines.get(
            case_id
        )

        if machine is None:
            machine = DecisionStateMachine()
            self._machines[case_id] = machine

        return machine

    def _require_machine(
        self,
        case_id: str,
    ) -> DecisionStateMachine:
        machine = self._machines.get(
            case_id
        )

        if machine is None:
            raise ValueError(
                f"No workflow exists for case "
                f"{case_id}."
            )

        return machine

    @staticmethod
    def _prepare_for_decision(
        machine: DecisionStateMachine,
        investigation: InvestigationResult | None,
    ) -> None:
        """
        Move a new case into the correct pre-decision state.

        Existing investigation results indicate that the case
        has already passed through investigation.
        """

        if machine.state == CaseState.OPEN:
            machine.start_verification()

        if machine.state == CaseState.VERIFICATION:
            if investigation is not None:
                machine.start_investigation()

            machine.start_decision()

        elif machine.state == CaseState.INVESTIGATION:
            machine.start_decision()

        elif machine.state == CaseState.REINVESTIGATION:
            machine.start_investigation()
            machine.start_decision()

        elif machine.state == CaseState.DECISION:
            return

        else:
            raise ValueError(
                f"Case is not eligible for a new "
                f"decision from state {machine.state.value}."
            )

    @staticmethod
    def _validate_investigation(
        verification: VerificationResult,
        investigation: InvestigationResult | None,
    ) -> None:
        """
        Ensure the investigation belongs to the supplied
        verification result.
        """

        if investigation is None:
            return

        if (
            verification.case_id
            != investigation.case_id
        ):
            raise ValueError(
                "Verification and investigation "
                "case IDs do not match."
            )

        discrepancy_ids = {
            discrepancy.discrepancy_id
            for discrepancy
            in verification.discrepancies
        }

        if (
            investigation.discrepancy_id
            not in discrepancy_ids
        ):
            raise ValueError(
                "Investigation discrepancy does not "
                "belong to the verification result."
            )

    @staticmethod
    def _build_workflow(
        *,
        case_id: str,
        machine: DecisionStateMachine,
        decision: DecisionResult | None,
        review_record: HumanReviewRecord | None = None,
    ) -> CaseWorkflow:
        """
        Build the persisted-style workflow representation.

        The state machine remains the source of truth for state.
        """

        existing_package = None

        if decision is not None and decision.decision in {
            DecisionOutcome.HUMAN_REVIEW,
            DecisionOutcome.RESOLVED_WITH_APPROVAL,
        }:
            existing_package = None

        review_records = []

        if review_record is not None:
            review_records.append(
                review_record
            )

        return CaseWorkflow(
            case_id=case_id,
            state=machine.state,
            decision=(
                decision.decision
                if decision is not None
                else None
            ),
            review_package=existing_package,
            review_records=review_records,
        )


def decide_case(
    verification: VerificationResult,
    investigation: InvestigationResult | None = None,
    *,
    policy: DecisionPolicy | None = None,
) -> DecisionServiceResult:
    """
    Convenience function for one-shot case decisioning.
    """

    return DecisionService(
        policy=policy
    ).decide(
        verification,
        investigation,
    )