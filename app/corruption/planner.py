import copy
import random

from app.corruption.engine import CorruptionEngine
from app.corruption.models import CorruptionEvent
from app.corruption.plan import CorruptionPlan


class CorruptionPlanner:

    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.engine = CorruptionEngine(seed)

    def apply(
        self,
        records: dict[str, list],
        case_ids: list[str],
        plan: CorruptionPlan,
    ) -> tuple[dict[str, list], list[CorruptionEvent]]:

        corrupted = copy.deepcopy(records)
        corruption_events: list[CorruptionEvent] = []

        if plan.total_corruptions > len(case_ids):
            raise ValueError(
                "Corruption plan cannot contain more "
                "operations than available cases"
            )

        selected_cases = self.rng.sample(
            case_ids,
            plan.total_corruptions,
        )

        cursor = 0

        for _ in range(plan.missing_records):
            case_id = selected_cases[cursor]
            cursor += 1

            corrupted, event = (
                self.engine.remove_bank_record(
                    corrupted,
                    case_id,
                )
            )

            corruption_events.append(event)

        for _ in range(plan.duplicate_records):
            case_id = selected_cases[cursor]
            cursor += 1

            corrupted, event = (
                self.engine.duplicate_bank_record(
                    corrupted,
                    case_id,
                )
            )

            corruption_events.append(event)

        for _ in range(plan.amount_mismatches):
            case_id = selected_cases[cursor]
            cursor += 1

            corrupted, event = (
                self.engine.change_bank_amount(
                    corrupted,
                    case_id,
                    difference=-1000,
                )
            )

            corruption_events.append(event)

        for _ in range(plan.reference_mismatches):
            case_id = selected_cases[cursor]
            cursor += 1

            wrong_case_number = (
                int(case_id.split("_")[1]) + 1
            )

            wrong_payment_id = (
                f"CASE_{wrong_case_number:04d}_PAYMENT"
            )

            corrupted, event = (
                self.engine.change_settlement_reference(
                    corrupted,
                    case_id,
                    wrong_payment_id,
                )
            )

            corruption_events.append(event)

        for _ in range(plan.timing_anomalies):
            case_id = selected_cases[cursor]
            cursor += 1

            corrupted, event = (
                self.engine.shift_settlement_time(
                    corrupted,
                    case_id,
                    minutes=-60,
                )
            )

            corruption_events.append(event)

        return corrupted, corruption_events