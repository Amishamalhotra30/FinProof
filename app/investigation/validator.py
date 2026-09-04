from decimal import Decimal

from app.investigation.models import (
    HypothesisStatus,
    InvestigationCase,
    InvestigationResult,
    InvestigationStatus,
)


class InvestigationValidationError(ValueError):
    """
    Raised when an InvestigationResult violates one or more
    deterministic Phase 6 invariants.
    """


class InvestigationResultValidator:
    """
    Deterministically validates a Phase 6 InvestigationResult.

    This component verifies structural and numerical consistency.

    It does not:
        - retrieve evidence
        - generate hypotheses
        - evaluate hypotheses
        - infer root causes
        - modify financial records
        - use an LLM

    The validator does not decide whether the investigation's
    conclusion is financially correct. It only verifies that
    the result is internally consistent with the InvestigationCase
    and its own declared findings.
    """

    def validate(
        self,
        case: InvestigationCase,
        result: InvestigationResult,
    ) -> InvestigationResult:
        """
        Validate an investigation result.

        A new result object is returned with validated=True
        when every deterministic invariant passes.

        The original result is not mutated.
        """

        errors = self._collect_errors(
            case,
            result,
        )

        if errors:
            raise InvestigationValidationError(
                "Investigation result validation failed: "
                + "; ".join(errors)
            )

        return result.model_copy(
            update={
                "validated": True,
            }
        )

    def is_valid(
        self,
        case: InvestigationCase,
        result: InvestigationResult,
    ) -> bool:
        """
        Return True when the investigation result satisfies
        every deterministic validation rule.
        """

        return not self._collect_errors(
            case,
            result,
        )

    def _collect_errors(
        self,
        case: InvestigationCase,
        result: InvestigationResult,
    ) -> list[str]:
        """
        Collect every validation failure rather than stopping
        at the first error.
        """

        errors: list[str] = []

        # ----------------------------------------------------
        # Identity consistency
        # ----------------------------------------------------

        if result.case_id != case.case_id:
            errors.append(
                "result.case_id does not match case.case_id"
            )

        if result.discrepancy_id != (
            case.discrepancy_id
        ):
            errors.append(
                "result.discrepancy_id does not match "
                "case.discrepancy_id"
            )

        # ----------------------------------------------------
        # Numerical sanity
        # ----------------------------------------------------

        if result.explained_amount < Decimal("0"):
            errors.append(
                "explained_amount cannot be negative"
            )

        if result.remaining_unexplained < Decimal("0"):
            errors.append(
                "remaining_unexplained cannot be negative"
            )

        discrepancy = abs(
            case.difference
        )

        if result.explained_amount > discrepancy:
            errors.append(
                "explained_amount cannot exceed the "
                "absolute discrepancy"
            )

        # ----------------------------------------------------
        # Conservation of discrepancy
        # ----------------------------------------------------

        total_explained = (
            result.explained_amount
            + result.remaining_unexplained
        )

        if total_explained != discrepancy:
            errors.append(
                "explained_amount + "
                "remaining_unexplained must equal "
                "absolute discrepancy"
            )

        # ----------------------------------------------------
        # Status invariants
        # ----------------------------------------------------

        if (
            result.status
            == InvestigationStatus.RESOLVED
            and result.remaining_unexplained
            != Decimal("0")
        ):
            errors.append(
                "RESOLVED investigation must have "
                "zero remaining_unexplained"
            )

        if (
            result.status
            == InvestigationStatus.RESOLVED
            and result.explained_amount
            != discrepancy
        ):
            errors.append(
                "RESOLVED investigation must explain "
                "the complete discrepancy"
            )

        if (
            result.status
            == InvestigationStatus.INSUFFICIENT_EVIDENCE
            and result.explained_amount
            != Decimal("0")
        ):
            errors.append(
                "INSUFFICIENT_EVIDENCE investigation "
                "cannot contain an explained amount"
            )

        if (
            result.status
            == InvestigationStatus.CONTRADICTION
            and result.explained_amount
            != Decimal("0")
        ):
            errors.append(
                "CONTRADICTION investigation cannot "
                "contain an explained amount"
            )

        # ----------------------------------------------------
        # Hypothesis-level invariants
        # ----------------------------------------------------

        supporting_ids: list[str] = []

        for finding in result.hypotheses:

            if finding.explained_amount < Decimal("0"):
                errors.append(
                    "hypothesis explained_amount cannot "
                    "be negative"
                )

            if finding.explained_amount > discrepancy:
                errors.append(
                    "hypothesis explained_amount cannot "
                    "exceed the discrepancy"
                )

            if (
                finding.status
                == HypothesisStatus.CONTRADICTED
                and finding.evidence_ids
            ):
                errors.append(
                    "CONTRADICTED hypothesis cannot contain "
                    "supporting evidence IDs"
                )

            supporting_ids.extend(
                finding.evidence_ids
            )

        # ----------------------------------------------------
        # Supporting evidence uniqueness
        # ----------------------------------------------------

        if len(supporting_ids) != len(
            set(supporting_ids)
        ):
            errors.append(
                "supporting evidence cannot be duplicated "
                "across hypothesis findings"
            )

        if len(
            result.supporting_evidence_ids
        ) != len(
            set(result.supporting_evidence_ids)
        ):
            errors.append(
                "result supporting evidence IDs "
                "cannot contain duplicates"
            )

        # ----------------------------------------------------
        # Result-level evidence consistency
        # ----------------------------------------------------

        result_evidence_ids = set(
            result.supporting_evidence_ids
        )

        finding_evidence_ids = set(
            supporting_ids
        )

        if result_evidence_ids != (
            finding_evidence_ids
        ):
            errors.append(
                "result supporting evidence IDs must "
                "match supporting hypothesis evidence IDs"
            )

        # ----------------------------------------------------
        # No negative explained amount hidden in findings
        # ----------------------------------------------------

        if (
            result.status
            in {
                InvestigationStatus.UNRESOLVED,
                InvestigationStatus.RESOLVED,
            }
            and not result.hypotheses
            and result.explained_amount
            > Decimal("0")
        ):
            errors.append(
                "positive explained amount requires "
                "at least one hypothesis finding"
            )

        return errors


def validate_investigation(
    case: InvestigationCase,
    result: InvestigationResult,
) -> InvestigationResult:
    """
    Convenience function for validating one investigation
    result.
    """

    return InvestigationResultValidator().validate(
        case,
        result,
    )


def is_valid_investigation(
    case: InvestigationCase,
    result: InvestigationResult,
) -> bool:
    """
    Convenience function for checking whether an
    investigation result is valid.
    """

    return InvestigationResultValidator().is_valid(
        case,
        result,
    )