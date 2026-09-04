from dataclasses import dataclass

from app.domain.graph import EventGraph
from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.reconstruction.event_chain import EventChain
from app.reconstruction.state_reconstructor import (
    ObservedFinancialState,
)


@dataclass(frozen=True)
class ReconstructionResult:
    """
    Complete output of Phase 4 reconstruction.

    Contains only what can be reconstructed from observed,
    reconciled evidence.

    It does not contain financial correctness judgments,
    root-cause analysis, or inferred missing events.
    """

    event_graph: EventGraph
    chains: tuple[EventChain, ...]
    chain_states: tuple[
        ObservedFinancialState,
        ...,
    ]
    batch_state: BatchReconstructionState

    @property
    def chain_count(self) -> int:
        return len(self.chains)

    @property
    def event_count(self) -> int:
        return self.event_graph.node_count

    @property
    def relationship_count(self) -> int:
        return self.event_graph.relationship_count

    @property
    def has_events(self) -> bool:
        return self.event_count > 0

    @property
    def has_relationships(self) -> bool:
        return self.relationship_count > 0