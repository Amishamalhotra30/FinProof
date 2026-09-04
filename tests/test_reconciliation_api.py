from datetime import datetime

from fastapi.testclient import TestClient

from app.evidence.graph import EvidenceGraph
from app.api.reconciliation import store
from app.main import app


client = TestClient(app)


def setup_function():

    store.clear()


def test_health():

    response = client.get(
        "/health"
    )

    assert response.status_code == 200

    assert response.json() == {
        "status": "ok"
    }


def test_reconcile_unknown_batch_returns_404():

    response = client.post(
        "/batches/BATCH_UNKNOWN/reconcile"
    )

    assert response.status_code == 404


def test_get_unknown_reconciliation_returns_404():

    response = client.get(
        "/batches/BATCH_UNKNOWN/reconciliation"
    )

    assert response.status_code == 404


def test_get_unknown_relationship_returns_404():

    response = client.get(
        "/relationships/REL_UNKNOWN"
    )

    assert response.status_code == 404


def test_get_unknown_ambiguous_batch_returns_404():

    response = client.get(
        "/batches/BATCH_UNKNOWN/"
        "reconciliation/ambiguous"
    )

    assert response.status_code == 404


def test_reconcile_empty_batch():

    store.register(
        "BATCH_001",
        EvidenceGraph(),
    )

    response = client.post(
        "/batches/BATCH_001/reconcile"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["batch_id"] == (
        "BATCH_001"
    )

    assert body["node_count"] == 0
    assert body["relationship_count"] == 0

    assert body["relationships"] == []
    assert body["review_items"] == []

    assert (
        body["metrics"][
            "relationships_processed"
        ]
        == 0
    )


def test_reconciliation_result_can_be_retrieved():

    store.register(
        "BATCH_002",
        EvidenceGraph(),
    )

    reconcile_response = client.post(
        "/batches/BATCH_002/reconcile"
    )

    assert (
        reconcile_response.status_code
        == 200
    )

    response = client.get(
        "/batches/BATCH_002/reconciliation"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["batch_id"] == (
        "BATCH_002"
    )


def test_reconciliation_metrics_are_exposed():

    store.register(
        "BATCH_003",
        EvidenceGraph(),
    )

    client.post(
        "/batches/BATCH_003/reconcile"
    )

    response = client.get(
        "/batches/BATCH_003/reconciliation"
    )

    metrics = response.json()["metrics"]

    expected_fields = {
        "relationships_processed",
        "confirmed_relationships",
        "ambiguous_relationships",
        "unresolved_relationships",
        "ai_assisted_relationships",
        "processing_time_ms",
        "relationship_precision",
        "relationship_recall",
        "ambiguity_rate",
        "ai_assisted_rate",
        "throughput",
    }

    assert expected_fields <= (
        set(metrics.keys())
    )


def test_ambiguous_endpoint_returns_empty_collection():

    store.register(
        "BATCH_004",
        EvidenceGraph(),
    )

    client.post(
        "/batches/BATCH_004/reconcile"
    )

    response = client.get(
        "/batches/BATCH_004/"
        "reconciliation/ambiguous"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["batch_id"] == (
        "BATCH_004"
    )

    assert body["count"] == 0
    assert body["items"] == []


def test_reconciliation_does_not_expose_ground_truth():

    store.register(
        "BATCH_005",
        EvidenceGraph(),
    )

    response = client.post(
        "/batches/BATCH_005/reconcile"
    )

    body = response.json()

    assert "ground_truth" not in body
    assert "ground_truth_relationships" not in body
    assert "ground_truth_events" not in body


def test_reconcile_is_idempotent_for_empty_batch():

    store.register(
        "BATCH_006",
        EvidenceGraph(),
    )

    first = client.post(
        "/batches/BATCH_006/reconcile"
    )

    second = client.post(
        "/batches/BATCH_006/reconcile"
    )

    assert first.status_code == 200
    assert second.status_code == 200

    first_body = first.json()
    second_body = second.json()

    assert (
        first_body["batch_id"]
        == second_body["batch_id"]
    )

    assert (
        first_body["relationship_count"]
        == second_body["relationship_count"]
    )


def test_api_uses_expected_routes():

    openapi = client.get(
        "/openapi.json"
    )

    assert openapi.status_code == 200

    paths = set(
        openapi.json()["paths"].keys()
    )

    assert (
        "/batches/{batch_id}/reconcile"
        in paths
    )

    assert (
        "/batches/{batch_id}/reconciliation"
        in paths
    )

    assert (
        "/relationships/{relationship_id}"
        in paths
    )

    assert (
        "/batches/{batch_id}/reconciliation/"
        "ambiguous"
        in paths
    )

def test_relationship_endpoint_after_reconciliation():

    store.register(
        "BATCH_007",
        EvidenceGraph(),
    )

    response = client.post(
        "/batches/BATCH_007/reconcile"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["relationships"] == []