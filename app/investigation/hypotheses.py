from app.investigation.models import (
    HypothesisStatus,
    HypothesisType,
    InvestigationCase,
    InvestigationHypothesis,
)


class HypothesisGenerator:
    """
    Deterministically generates bounded candidate hypotheses
    for a Phase 6 investigation case.

    This component does not:
        - retrieve evidence
        - determine the root cause
        - calculate explained amounts
        - assign confidence
        - use an LLM
        - modify the investigation case

    It only maps a Phase 5 control failure to a controlled
    set of possible financial explanations.
    """

    CONTROL_HYPOTHESES: dict[
        str,
        tuple[HypothesisType, ...],
    ] = {
        "SETTLEMENT_AMOUNT": (
            HypothesisType.PARTIAL_SETTLEMENT,
            HypothesisType.BUNDLED_SETTLEMENT,
            HypothesisType.REFUND,
            HypothesisType.FEE,
            HypothesisType.TAX,
            HypothesisType.ADJUSTMENT,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "BANK_CREDIT_AMOUNT": (
            HypothesisType.PARTIAL_SETTLEMENT,
            HypothesisType.BUNDLED_SETTLEMENT,
            HypothesisType.MISSING_EVENT,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "REFUND_AMOUNT": (
            HypothesisType.REFUND,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "FEE_AMOUNT": (
            HypothesisType.FEE,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "ADJUSTMENT_AMOUNT": (
            HypothesisType.ADJUSTMENT,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "PAYMENT_SETTLEMENT_COMPLETENESS": (
            HypothesisType.PARTIAL_SETTLEMENT,
            HypothesisType.BUNDLED_SETTLEMENT,
            HypothesisType.MISSING_EVENT,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "SETTLEMENT_BANK_COMPLETENESS": (
            HypothesisType.PARTIAL_SETTLEMENT,
            HypothesisType.BUNDLED_SETTLEMENT,
            HypothesisType.MISSING_EVENT,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "REFUND_PAYMENT_COMPLETENESS": (
            HypothesisType.REFUND,
            HypothesisType.MISSING_EVENT,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "DUPLICATE_EVENT": (
            HypothesisType.DUPLICATE_EVENT,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "EVENT_ORDERING": (
            HypothesisType.TIMING_DIFFERENCE,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "SETTLEMENT_TIMING": (
            HypothesisType.TIMING_DIFFERENCE,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "CHAIN_TEMPORAL_ORDER": (
            HypothesisType.TIMING_DIFFERENCE,
            HypothesisType.SOURCE_DATA_ERROR,
        ),
        "CURRENCY_CONSISTENCY": (
            HypothesisType.SOURCE_DATA_ERROR,
        ),
    }

    DEFAULT_HYPOTHESES: tuple[
        HypothesisType,
        ...
    ] = (
        HypothesisType.SOURCE_DATA_ERROR,
        HypothesisType.UNDETERMINED,
    )

    def generate(
        self,
        case: InvestigationCase,
    ) -> list[InvestigationHypothesis]:
        """
        Generate candidate hypotheses for one investigation case.

        Candidates are always returned in a deterministic order.
        """

        hypothesis_types = self.CONTROL_HYPOTHESES.get(
            case.control_failure,
            self.DEFAULT_HYPOTHESES,
        )

        return [
            self._build_hypothesis(
                case,
                hypothesis_type,
                index,
            )
            for index, hypothesis_type in enumerate(
                hypothesis_types,
                start=1,
            )
        ]

    @staticmethod
    def _build_hypothesis(
        case: InvestigationCase,
        hypothesis_type: HypothesisType,
        index: int,
    ) -> InvestigationHypothesis:
        return InvestigationHypothesis(
            hypothesis_id=(
                f"{case.case_id}_"
                f"{case.discrepancy_id}_"
                f"H{index:02d}"
            ),
            hypothesis_type=hypothesis_type,
            status=HypothesisStatus.UNDETERMINED,
            description=(
                HypothesisGenerator._description(
                    hypothesis_type
                )
            ),
            evidence_ids=[],
            explained_amount=0,
            contradicting_evidence_ids=[],
            required_evidence=[],
        )

    @staticmethod
    def _description(
        hypothesis_type: HypothesisType,
    ) -> str:
        descriptions = {
            HypothesisType.REFUND:
                "A refund may explain part of the observed financial difference.",

            HypothesisType.FEE:
                "A fee may explain part of the observed financial difference.",

            HypothesisType.TAX:
                "A tax component may explain part of the observed financial difference.",

            HypothesisType.ADJUSTMENT:
                "An adjustment may explain part of the observed financial difference.",

            HypothesisType.PARTIAL_SETTLEMENT:
                "Only part of the expected amount may have been settled.",

            HypothesisType.BUNDLED_SETTLEMENT:
                "The observed settlement may represent multiple financial events bundled together.",

            HypothesisType.DUPLICATE_EVENT:
                "A duplicated financial event may have affected the observed state.",

            HypothesisType.TIMING_DIFFERENCE:
                "A difference in event timing may explain the observed discrepancy.",

            HypothesisType.MISSING_EVENT:
                "A required financial event may be absent from the observed evidence.",

            HypothesisType.SOURCE_DATA_ERROR:
                "The source evidence may contain an incorrect or inconsistent value.",

            HypothesisType.UNDETERMINED:
                "The available information is insufficient to determine a specific explanation.",
        }

        return descriptions[hypothesis_type]


def generate_hypotheses(
    case: InvestigationCase,
) -> list[InvestigationHypothesis]:
    """
    Convenience function for generating hypotheses.
    """

    return HypothesisGenerator().generate(case)