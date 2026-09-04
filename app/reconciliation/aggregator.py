from dataclasses import dataclass
from decimal import Decimal

from app.domain.records import (
    BankStatementLine,
    FeeRecord,
    PaymentRecord,
    RefundRecord,
    SettlementRecord,
)


@dataclass
class CaseRecords:
    case_id: str

    payment: PaymentRecord | None
    refunds: list[RefundRecord]
    fees: list[FeeRecord]
    settlements: list[SettlementRecord]
    bank_lines: list[BankStatementLine]

    @property
    def refund_amount(self) -> Decimal:
        return sum(
            (
                refund.amount
                for refund in self.refunds
            ),
            Decimal("0.00"),
        )

    @property
    def fee_amount(self) -> Decimal:
        return sum(
            (
                fee.amount
                for fee in self.fees
            ),
            Decimal("0.00"),
        )

    @property
    def settlement_amount(self) -> Decimal:
        return sum(
            (
                settlement.net_amount
                for settlement in self.settlements
            ),
            Decimal("0.00"),
        )

    @property
    def bank_amount(self) -> Decimal:
        return sum(
            (
                bank.credit
                for bank in self.bank_lines
            ),
            Decimal("0.00"),
        )


def aggregate_records(
    records: dict[str, list],
) -> dict[str, CaseRecords]:

    cases: dict[str, CaseRecords] = {}

    # ---------------------------------------------------------
    # Payments define the cases.
    # ---------------------------------------------------------

    for payment in records["payments"]:
        cases[payment.payment_id] = CaseRecords(
            case_id=payment.payment_id,
            payment=payment,
            refunds=[],
            fees=[],
            settlements=[],
            bank_lines=[],
        )

    # ---------------------------------------------------------
    # Refunds belong to payments through payment_id.
    # ---------------------------------------------------------

    for refund in records["refunds"]:
        case = cases.get(refund.payment_id)

        if case is not None:
            case.refunds.append(refund)

    # ---------------------------------------------------------
    # Fees belong to payments through payment_id.
    # ---------------------------------------------------------

    for fee in records["fees"]:
        case = cases.get(fee.payment_id)

        if case is not None:
            case.fees.append(fee)

    # ---------------------------------------------------------
    # Settlements belong to payments through payment_id.
    # ---------------------------------------------------------

    for settlement in records["settlements"]:

        if settlement.payment_id is None:
            continue

        case = cases.get(
            settlement.payment_id
        )

        if case is not None:
            case.settlements.append(
                settlement
            )

    # ---------------------------------------------------------
    # Bank records are assigned independently.
    #
    # We deliberately DO NOT use settlement.payment_id here.
    # The bank record has its own bank_txn_id, which preserves
    # the original case identity even if a settlement reference
    # has been corrupted.
    # ---------------------------------------------------------

    for bank_line in records["bank"]:

        bank_txn_id = bank_line.bank_txn_id

        if "_BANK" not in bank_txn_id:
            continue

        case_prefix = bank_txn_id.rsplit(
            "_BANK",
            1,
        )[0]

        payment_id = (
            f"{case_prefix}_PAYMENT"
        )

        case = cases.get(payment_id)

        if case is not None:
            case.bank_lines.append(
                bank_line
            )

    return cases