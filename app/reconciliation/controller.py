from app.reconciliation.aggregator import (
    aggregate_records,
)
from app.reconciliation.matcher import (
    reconcile_case,
)
from app.reconciliation.models import (
    ReconciliationResult,
)


def reconcile_records(
    records: dict[str, list],
) -> list[ReconciliationResult]:

    cases = aggregate_records(records)

    results: list[ReconciliationResult] = []

    for case in cases.values():

        if case.payment is None:
            continue

        result = reconcile_case(
            case_id=case.case_id,
            payment_amount=case.payment.amount,
            refund_amount=case.refund_amount,
            fee_amount=case.fee_amount,
            settlement_amount=case.settlement_amount,
            bank_amount=case.bank_amount,
        )

        results.append(result)

    return results