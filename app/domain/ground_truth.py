from pydantic import BaseModel

from app.domain.graph import EventGraph


class GroundTruthCase(BaseModel):
    case_id: str
    scenario: str
    event_graph: EventGraph


class GroundTruthBatch(BaseModel):
    batch_id: str
    seed: int
    cases: list[GroundTruthCase]

    def scenario_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}

        for case in self.cases:
            counts[case.scenario] = counts.get(case.scenario, 0) + 1

        return counts