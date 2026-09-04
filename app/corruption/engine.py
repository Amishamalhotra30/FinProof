import copy
import random

from app.corruption.models import (
    CorruptionEvent,
    CorruptionType,
)


class CorruptionEngine:

    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def remove_bank_record(
        self,
        records: dict[str, list],
        case_id: str,
    ) -> tuple[dict[str, list], CorruptionEvent]:

        corrupted = copy.deepcopy(records)

        bank_records = corrupted["bank"]

        target_index = None
        target_record = None

        for index, record in enumerate(bank_records):
            if case_id in record.bank_txn_id:
                target_index = index
                target_record = record
                break

        if target_index is None or target_record is None:
            raise ValueError(
                f"No bank record found for case {case_id}"
            )

        del bank_records[target_index]

        event = CorruptionEvent(
            case_id=case_id,
            corruption_type=CorruptionType.MISSING_RECORD,
            record_type="bank",
            record_id=target_record.bank_txn_id,
            description="Bank record removed",
        )

        return corrupted, event

    def duplicate_bank_record(
        self,
        records: dict[str, list],
        case_id: str,
    ) -> tuple[dict[str, list], CorruptionEvent]:

        corrupted = copy.deepcopy(records)

        bank_records = corrupted["bank"]

        target_record = None

        for record in bank_records:
            if case_id in record.bank_txn_id:
                target_record = record
                break

        if target_record is None:
            raise ValueError(
                f"No bank record found for case {case_id}"
            )

        duplicated_record = copy.deepcopy(target_record)

        bank_records.append(duplicated_record)

        event = CorruptionEvent(
            case_id=case_id,
            corruption_type=CorruptionType.DUPLICATE_RECORD,
            record_type="bank",
            record_id=target_record.bank_txn_id,
            description="Bank record duplicated",
        )

        return corrupted, event

    def change_bank_amount(
        self,
        records: dict[str, list],
        case_id: str,
        difference: int,
    ) -> tuple[dict[str, list], CorruptionEvent]:

        corrupted = copy.deepcopy(records)

        bank_records = corrupted["bank"]

        target_record = None

        for record in bank_records:
            if case_id in record.bank_txn_id:
                target_record = record
                break

        if target_record is None:
            raise ValueError(
                f"No bank record found for case {case_id}"
            )

        if difference == 0:
            raise ValueError(
                "difference must be non-zero"
            )

        target_record.credit += difference

        event = CorruptionEvent(
            case_id=case_id,
            corruption_type=CorruptionType.AMOUNT_MISMATCH,
            record_type="bank",
            record_id=target_record.bank_txn_id,
            description=(
                f"Bank credit changed by {difference}"
            ),
        )

        return corrupted, event
    def change_settlement_reference(
        self,
        records: dict[str, list],
        case_id: str,
        wrong_payment_id: str,
    ) -> tuple[dict[str, list], CorruptionEvent]:

        corrupted = copy.deepcopy(records)

        settlement_records = corrupted["settlements"]

        target_record = None

        for record in settlement_records:
            if case_id in record.settlement_id:
                target_record = record
                break

        if target_record is None:
            raise ValueError(
                f"No settlement record found for case {case_id}"
            )

        if target_record.payment_id == wrong_payment_id:
            raise ValueError(
                "wrong_payment_id must differ from "
                "the original payment_id"
            )

        original_payment_id = target_record.payment_id

        target_record.payment_id = wrong_payment_id

        event = CorruptionEvent(
            case_id=case_id,
            corruption_type=CorruptionType.REFERENCE_MISMATCH,
            record_type="settlement",
            record_id=target_record.settlement_id,
            description=(
                f"Settlement payment reference changed "
                f"from {original_payment_id} "
                f"to {wrong_payment_id}"
            ),
        )

        return corrupted, event
    def shift_settlement_time(
        self,
        records: dict[str, list],
        case_id: str,
        minutes: int,
    ) -> tuple[dict[str, list], CorruptionEvent]:

        corrupted = copy.deepcopy(records)

        settlement_records = corrupted["settlements"]

        target_record = None

        for record in settlement_records:
            if case_id in record.settlement_id:
                target_record = record
                break

        if target_record is None:
            raise ValueError(
                f"No settlement record found for case {case_id}"
            )

        if minutes == 0:
            raise ValueError(
                "minutes must be non-zero"
            )

        from datetime import timedelta

        target_record.settled_at = (
            target_record.settled_at
            + timedelta(minutes=minutes)
        )

        event = CorruptionEvent(
            case_id=case_id,
            corruption_type=CorruptionType.TIMING_ANOMALY,
            record_type="settlement",
            record_id=target_record.settlement_id,
            description=(
                f"Settlement timestamp shifted by "
                f"{minutes} minutes"
            ),
        )

        return corrupted, event