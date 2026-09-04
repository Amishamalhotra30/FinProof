from dataclasses import dataclass
from decimal import Decimal

from app.reconciliation.aggregator import CaseRecords


@dataclass(frozen=True)
class VerificationIssue:
    rule: str
    reason: str


def verify_case(
    case: CaseRecords,
) -> list[VerificationIssue]:

    issues: list[VerificationIssue] = []

    if case.payment is None:
        issues.append(
            VerificationIssue(
                rule="PAYMENT_MISSING",
                reason="Payment record is missing",
            )
        )

        return issues

    expected_amount = (
        case.payment.amount
        - case.refund_amount
        - case.fee_amount
    )

    if case.settlement_amount != expected_amount:
        issues.append(
            VerificationIssue(
                rule="SETTLEMENT_AMOUNT_MISMATCH",
                reason=(
                    f"Expected settlement "
                    f"{expected_amount}, "
                    f"found {case.settlement_amount}"
                ),
            )
        )

    if case.bank_amount != case.settlement_amount:
        issues.append(
            VerificationIssue(
                rule="BANK_AMOUNT_MISMATCH",
                reason=(
                    f"Expected bank credit "
                    f"{case.settlement_amount}, "
                    f"found {case.bank_amount}"
                ),
            )
        )

    for settlement in case.settlements:

        if settlement.payment_id != case.payment.payment_id:
            issues.append(
                VerificationIssue(
                    rule="REFERENCE_MISMATCH",
                    reason=(
                        f"Settlement "
                        f"{settlement.settlement_id} "
                        f"references "
                        f"{settlement.payment_id} "
                        f"instead of "
                        f"{case.payment.payment_id}"
                    ),
                )
            )

        if settlement.settled_at < case.payment.captured_at:
            issues.append(
                VerificationIssue(
                    rule="TIMING_ANOMALY",
                    reason=(
                        f"Settlement "
                        f"{settlement.settlement_id} "
                        f"occurred before payment capture"
                    ),
                )
            )

        if settlement.utr is not None:

            matching_bank_lines = [
                bank
                for bank in case.bank_lines
                if bank.utr == settlement.utr
            ]

            if not matching_bank_lines:
                issues.append(
                    VerificationIssue(
                        rule="REFERENCE_MISMATCH",
                        reason=(
                            f"Settlement "
                            f"{settlement.settlement_id} "
                            f"has UTR "
                            f"{settlement.utr} "
                            f"but no matching bank "
                            f"transaction exists in this case"
                        ),
                    )
                )

    return issues