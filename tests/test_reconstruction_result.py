from decimal import Decimal

from app.domain.graph import EventGraph
from app.reconstruction.batch_state import (
    BatchReconstructionState,
)
from app.reconstruction.event_chain import EventChain
from app.reconstruction.result import (
    ReconstructionResult,
)
from app.reconstruction.state_reconstructor import (
    ObservedFinancialState,
)


def make_result():

    graph = EventGraph()

    chain = EventChain(
        chain_id="CHAIN_001",
        event_ids=[],
    )

    chain_state = ObservedFinancialState(
        chain_id="CHAIN_001",
        gross_amount=Decimal("50000"),
    )

    batch_state = BatchReconstructionState(
        chain_count=1,
        total_gross_amount=Decimal("50000"),
    )

    return ReconstructionResult(
        event_graph=graph,
        chains=(chain,),
        chain_states=(chain_state,),
        batch_state=batch_state,
    )


def test_result_contains_reconstruction_outputs():

    result = make_result()

    assert result.event_graph is not None
    assert len(result.chains) == 1
    assert len(result.chain_states) == 1
    assert result.batch_state is not None


def test_chain_count():

    result = make_result()

    assert result.chain_count == 1


def test_event_count():

    result = make_result()

    assert result.event_count == 0


def test_relationship_count():

    result = make_result()

    assert result.relationship_count == 0


def test_has_events():

    result = make_result()

    assert result.has_events is False


def test_has_relationships():

    result = make_result()

    assert result.has_relationships is False


def test_batch_state_is_preserved():

    result = make_result()

    assert (
        result.batch_state.total_gross_amount
        == Decimal("50000")
    )


def test_result_is_immutable():

    result = make_result()

    try:
        result.chains = ()
        raise AssertionError(
            "ReconstructionResult should be immutable"
        )
    except AttributeError:
        pass