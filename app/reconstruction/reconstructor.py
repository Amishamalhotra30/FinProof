from app.reconciliation.graph import ReconciliationGraph
from app.reconstruction.batch_state import (
    BatchStateReconstructor,
)
from app.reconstruction.event_chain import (
    EventChainBuilder,
)
from app.reconstruction.event_graph_builder import (
    EventGraphBuilder,
)
from app.reconstruction.result import (
    ReconstructionResult,
)
from app.reconstruction.state_reconstructor import (
    StateReconstructor,
)


class Reconstructor:
    """
    Phase 4 orchestration layer.

    Pipeline:

        ReconciliationGraph
              ↓
        EventGraphBuilder
              ↓
        EventGraph
              ↓
        EventChainBuilder
              ↓
        EventChain
              ↓
        StateReconstructor
              ↓
        BatchStateReconstructor
              ↓
        ReconstructionResult

    This layer performs reconstruction only.

    It does not:
        - repair records
        - create missing events
        - determine financial correctness
        - investigate discrepancies
        - access ground truth
    """

    def __init__(
        self,
        event_graph_builder: EventGraphBuilder | None = None,
        chain_builder: EventChainBuilder | None = None,
        state_reconstructor: StateReconstructor | None = None,
        batch_state_reconstructor: (
            BatchStateReconstructor | None
        ) = None,
    ):
        self.event_graph_builder = (
            event_graph_builder
            or EventGraphBuilder()
        )

        self.chain_builder = (
            chain_builder
            or EventChainBuilder()
        )

        self.state_reconstructor = (
            state_reconstructor
            or StateReconstructor()
        )

        self.batch_state_reconstructor = (
            batch_state_reconstructor
            or BatchStateReconstructor(
                self.state_reconstructor
            )
        )

    def reconstruct(
        self,
        reconciliation_graph: ReconciliationGraph,
    ) -> ReconstructionResult:

        # -------------------------------------------------
        # Step 1:
        # Convert reconciled records into domain events.
        # -------------------------------------------------

        event_graph = (
            self.event_graph_builder.build(
                reconciliation_graph
            )
        )

        # -------------------------------------------------
        # Step 2:
        # Build observed event chains.
        # -------------------------------------------------

        chains = self.chain_builder.build(
            event_graph
        )

        # -------------------------------------------------
        # Step 3:
        # Convert domain events into a flat list for
        # state reconstruction.
        # -------------------------------------------------

        events = list(
            event_graph.events.values()
        )

        # -------------------------------------------------
        # Step 4:
        # Reconstruct state independently for every chain.
        # -------------------------------------------------

        chain_states = tuple(
            self.state_reconstructor.reconstruct(
                chain,
                events,
            )
            for chain in chains
        )

        # -------------------------------------------------
        # Step 5:
        # Aggregate chain states into batch state.
        # -------------------------------------------------

        batch_state = (
            self.batch_state_reconstructor.aggregate(
                list(chain_states)
            )
        )

        return ReconstructionResult(
            event_graph=event_graph,
            chains=tuple(chains),
            chain_states=chain_states,
            batch_state=batch_state,
        )