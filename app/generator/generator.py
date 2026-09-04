from datetime import datetime, timedelta
from decimal import Decimal
import random

from app.domain.enums import ScenarioType
from app.domain.ground_truth import GroundTruthBatch, GroundTruthCase
from app.generator.registry import SCENARIO_GENERATORS


SCENARIO_WEIGHTS = {
    ScenarioType.NORMAL_SETTLEMENT: 0.50,
    ScenarioType.PARTIAL_REFUND: 0.25,
    ScenarioType.SPLIT_SETTLEMENT: 0.25,
}


def choose_scenario(rng: random.Random) -> ScenarioType:
    scenarios = list(SCENARIO_WEIGHTS.keys())
    weights = list(SCENARIO_WEIGHTS.values())

    return rng.choices(
        scenarios,
        weights=weights,
        k=1,
    )[0]


def generate_batch(
    num_cases: int,
    seed: int,
) -> GroundTruthBatch:
    if num_cases <= 0:
        raise ValueError("num_cases must be positive")

    rng = random.Random(seed)

    cases: list[GroundTruthCase] = []

    start_time = datetime(2026, 8, 30, 9, 0, 0)

    for index in range(1, num_cases + 1):
        case_id = f"CASE_{index:04d}"

        payment_amount = Decimal(
            rng.randrange(1000, 1000000)
        ).quantize(Decimal("0.01"))

        fee_amount = (
            payment_amount * Decimal("0.02")
        ).quantize(Decimal("0.01"))

        max_refund = int(
            payment_amount * Decimal("0.30")
        )

        refund_amount = Decimal(
            rng.randrange(0, max_refund + 1)
        ).quantize(Decimal("0.01"))

        base_time = start_time + timedelta(
            minutes=(index - 1) * 20
        )

        scenario = choose_scenario(rng)

        if scenario == ScenarioType.PARTIAL_REFUND:
            if refund_amount == Decimal("0.00"):
                refund_amount = Decimal("1.00")

        generator = SCENARIO_GENERATORS[scenario]

        graph = generator(
            case_id,
            base_time,
            payment_amount,
            refund_amount,
            fee_amount,
        )

        cases.append(
            GroundTruthCase(
                case_id=case_id,
                scenario=scenario.value,
                event_graph=graph,
            )
        )

    return GroundTruthBatch(
        batch_id=f"BATCH_{seed}",
        seed=seed,
        cases=cases,
    )