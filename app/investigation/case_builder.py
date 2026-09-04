from decimal import Decimal

from app.investigation.models import InvestigationCase
from app.verification.models import (
    Discrepancy,
    VerificationResult,
)


class InvestigationCaseBuilder:
    """
    Converts Phase 5 verification discrepancies into
    structured Phase 6 investigation cases.

    This component does not:
        - generate hypotheses
        - retrieve evidence
        - infer root causes
        - calculate financial explanations
        - use an LLM

    It only establishes the Phase 5 -> Phase 6 boundary.
    """

    def build(
        self,
        verification: VerificationResult,
        discrepancy: Discrepancy,
    ) -> InvestigationCase:
        """
        Build one investigation case from one Phase 5
        discrepancy.
        """

        return InvestigationCase(
            case_id=verification.case_id,
            discrepancy_id=discrepancy.discrepancy_id,
            control_failure=discrepancy.control_id,
            affected_event_ids=list(
                discrepancy.affected_event_ids
            ),
            expected_value=discrepancy.expected_value,
            observed_value=discrepancy.observed_value,
            difference=discrepancy.difference,
            expected_state=self._decimal_dict(
                verification.expected_state
            ),
            observed_state=self._decimal_dict(
                verification.observed_state
            ),
        )

    @staticmethod
    def _decimal_dict(value) -> dict[str, Decimal]:
        """
        Convert a Phase 5 financial-state object into a
        dictionary containing its financial values.

        No financial calculation or interpretation occurs here.
        The builder only preserves the state supplied by Phase 5.
        """

        if value is None:
            return {}

        # Pydantic models
        if hasattr(value, "model_dump"):
            value = value.model_dump()

        # Ordinary dictionaries
        if isinstance(value, dict):
            return {
                str(key): item
                for key, item in value.items()
                if isinstance(item, Decimal)
            }

        return {}


def build_investigation_case(
    verification: VerificationResult,
    discrepancy: Discrepancy,
) -> InvestigationCase:
    """
    Convenience function for building one investigation case.
    """

    return InvestigationCaseBuilder().build(
        verification,
        discrepancy,
    )


def build_investigation_cases(
    verification: VerificationResult,
) -> list[InvestigationCase]:
    """
    Build one investigation case for every discrepancy
    produced by Phase 5.
    """

    builder = InvestigationCaseBuilder()

    return [
        builder.build(
            verification,
            discrepancy,
        )
        for discrepancy in verification.discrepancies
    ]