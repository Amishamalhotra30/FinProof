from collections.abc import Callable
from datetime import datetime
from decimal import Decimal

from app.domain.enums import ScenarioType
from app.domain.graph import EventGraph
from app.generator.scenarios import (
    generate_normal_settlement,
    generate_partial_refund,
    generate_split_settlement,
)


ScenarioGenerator = Callable[
    [
        str,
        datetime,
        Decimal,
        Decimal,
        Decimal,
    ],
    EventGraph,
]


SCENARIO_GENERATORS: dict[
    ScenarioType,
    ScenarioGenerator,
] = {
    ScenarioType.NORMAL_SETTLEMENT:
        generate_normal_settlement,

    ScenarioType.PARTIAL_REFUND:
        generate_partial_refund,

    ScenarioType.SPLIT_SETTLEMENT:
        generate_split_settlement,
}