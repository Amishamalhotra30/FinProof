from app.application.batch_runtime import (
    BatchRuntimeStore,
)
from app.application.models import (
    BatchStatus,
)
from app.application.pipeline import (
    FinProofPipeline,
)
from app.evidence.graph import EvidenceGraph


def test_batch_runtime_store_creates_and_retrieves_batch():
    store = BatchRuntimeStore()

    runtime = store.create(
        batch_id="phase9-test-001",
        name="Phase 9 Test Batch",
        scenario="NORMAL",
        seed=42,
    )

    assert runtime.metadata.batch_id == "phase9-test-001"
    assert runtime.metadata.name == "Phase 9 Test Batch"
    assert runtime.metadata.scenario == "NORMAL"
    assert runtime.metadata.seed == 42
    assert runtime.metadata.status == BatchStatus.CREATED

    retrieved = store.get("phase9-test-001")

    assert retrieved is runtime
    assert store.exists("phase9-test-001")


def test_batch_runtime_store_rejects_duplicate_batch():
    store = BatchRuntimeStore()

    store.create(
        batch_id="phase9-test-duplicate",
        name="First",
        scenario="NORMAL",
        seed=42,
    )

    try:
        store.create(
            batch_id="phase9-test-duplicate",
            name="Second",
            scenario="NORMAL",
            seed=43,
        )
        assert False, "Expected duplicate batch rejection"
    except ValueError as exc:
        assert "Batch already exists" in str(exc)


def test_pipeline_runs_complete_runtime_flow():
    store = BatchRuntimeStore()

    runtime = store.create(
        batch_id="phase9-pipeline-001",
        name="Pipeline Test",
        scenario="NORMAL",
        seed=42,
    )

    result = FinProofPipeline().run(
        runtime,
        EvidenceGraph(),
    )

    assert result.batch_id == "phase9-pipeline-001"
    assert result.status == BatchStatus.COMPLETED
    assert result.total_duration_ms >= 0
    assert result.reconciliation_duration_ms >= 0
    assert result.reconstruction_duration_ms >= 0
    assert result.verification_duration_ms >= 0
    assert result.investigation_duration_ms >= 0

    assert runtime.metadata.status == BatchStatus.COMPLETED

    assert runtime.evidence_graph is not None
    assert runtime.reconciliation_result is not None
    assert runtime.reconstruction_result is not None
    assert runtime.verification_result is not None
    assert runtime.investigation_result is not None


def test_pipeline_completes_all_stages():
    runtime = BatchRuntimeStore().create(
        batch_id="phase9-pipeline-stages",
        name="Stage Test",
        scenario="NORMAL",
        seed=42,
    )

    FinProofPipeline().run(
        runtime,
        EvidenceGraph(),
    )

    stages = {
        stage.name: stage
        for stage in runtime.stages
    }

    assert "reconciliation" in stages
    assert "reconstruction" in stages
    assert "verification" in stages
    assert "investigation" in stages

    assert stages["reconciliation"].status == "COMPLETED"
    assert stages["reconstruction"].status == "COMPLETED"
    assert stages["verification"].status == "COMPLETED"
    assert stages["investigation"].status == "COMPLETED"

    for stage in stages.values():
        assert stage.duration_ms >= 0


def test_pipeline_uses_supplied_batch_runtime():
    store = BatchRuntimeStore()

    runtime = store.create(
        batch_id="phase9-runtime-reference",
        name="Reference Test",
        scenario="NORMAL",
        seed=123,
    )

    FinProofPipeline().run(
        runtime,
        EvidenceGraph(),
    )

    assert store.get(
        "phase9-runtime-reference"
    ) is runtime


def test_batch_runtime_financial_impact_is_zero_without_discrepancies():
    runtime = BatchRuntimeStore().create(
        batch_id="phase9-impact-001",
        name="Impact Test",
        scenario="NORMAL",
        seed=42,
    )

    FinProofPipeline().run(
        runtime,
        EvidenceGraph(),
    )

    assert runtime.financial_impact == 0


def test_pipeline_does_not_require_ground_truth():
    runtime = BatchRuntimeStore().create(
        batch_id="phase9-ground-truth-001",
        name="Ground Truth Isolation",
        scenario="NORMAL",
        seed=42,
    )

    pipeline = FinProofPipeline()

    # The production runtime accepts only observed evidence.
    # There is intentionally no ground-truth argument.
    result = pipeline.run(
        runtime,
        EvidenceGraph(),
    )

    assert result.status == BatchStatus.COMPLETED