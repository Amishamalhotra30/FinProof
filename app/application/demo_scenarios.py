from __future__ import annotations

from decimal import Decimal


def apply_demo_scenario(
    records: dict,
    scenario: str,
) -> dict:
    """
    Phase 9 demo-only scenario adapter.

    This deliberately introduces observable financial
    mismatches for demo scenarios without changing any
    production reconciliation, reconstruction,
    verification, investigation, or decision logic.
    """

    scenario = scenario.strip().upper()

    if scenario == "NORMAL":
        return records

    result = dict(records)

    settlements = list(
        result.get("settlements", [])
    )

    if not settlements:
        return result

    def corrupt(index: int, amount: str) -> None:
        if index >= len(settlements):
            return

        settlement = settlements[index]

        settlements[index] = settlement.model_copy(
            update={
                "net_amount": (
                    settlement.net_amount
                    + Decimal(amount)
                )
            }
        )

    if scenario == "MIXED":
        for index in (4, 14, 24, 34, 44):
            corrupt(index, "125.00")

    elif scenario == "FAILURE_HEAVY":
        for index in range(0, len(settlements), 5):
            corrupt(index, "500.00")

    elif scenario == "ADVERSARIAL":
        for index in (3, 17, 31, 47, 63):
            corrupt(index, "2500.00")

    result["settlements"] = settlements

    return result