from decimal import Decimal

from app.reconciliation.models import (
    MatchStatus,
    ReconciliationResult,
)


def reconcile_case(
    case_id: str,
    payment_amount: Decimal,
    refund_amount: Decimal,
    fee_amount: Decimal,
    settlement_amount: Decimal,
    bank_amount: Decimal,
) -> ReconciliationResult:

    expected_amount = (
        payment_amount
        - refund_amount
        - fee_amount
    )

    if settlement_amount != expected_amount:
        return ReconciliationResult(
            case_id=case_id,
            status=MatchStatus.EXCEPTION,
            confidence=Decimal("1.00"),
            reason=(
                "Settlement amount does not match "
                "expected net amount"
            ),
        )

    if bank_amount != settlement_amount:
        return ReconciliationResult(
            case_id=case_id,
            status=MatchStatus.EXCEPTION,
            confidence=Decimal("1.00"),
            reason=(
                "Bank credit does not match "
                "settlement amount"
            ),
        )

    return ReconciliationResult(
        case_id=case_id,
        status=MatchStatus.MATCH,
        confidence=Decimal("1.00"),
        reason="Payment, settlement and bank amounts reconcile",
    )