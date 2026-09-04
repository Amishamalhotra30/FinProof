from fastapi.testclient import TestClient

from app.api.batches import pipeline
from app.application.batch_runtime import store
from app.main import app


client = TestClient(app)


def setup_function():
    store.clear()


def teardown_function():
    store.clear()


def test_create_batch():
    response = client.post(
        "/batches",
        json={
            "name": "API Test Batch",
            "scenario": "NORMAL",
            "seed": 42,
            "num_cases": 5,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["name"] == "API Test Batch"
    assert body["scenario"] == "NORMAL"
    assert body["seed"] == 42
    assert body["status"] == "CREATED"
    assert body["case_count"] == 0


def test_unknown_batch_returns_404():
    response = client.get(
        "/batches/does-not-exist"
    )

    assert response.status_code == 404


def test_invalid_scenario_returns_422():
    response = client.post(
        "/batches",
        json={
            "name": "Invalid Scenario",
            "scenario": "UNKNOWN",
            "seed": 42,
            "num_cases": 5,
        },
    )

    assert response.status_code == 422


def test_duplicate_batch_returns_409():
    payload = {
        "name": "Duplicate Test",
        "scenario": "NORMAL",
        "seed": 42,
        "num_cases": 5,
    }

    first = client.post(
        "/batches",
        json=payload,
    )

    second = client.post(
        "/batches",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 409


def test_ingestion_report():
    response = client.post(
        "/batches",
        json={
            "name": "Ingestion Test",
            "scenario": "NORMAL",
            "seed": 42,
            "num_cases": 5,
        },
    )

    assert response.status_code == 200

    batch_id = response.json()["batch_id"]

    report = client.get(
        f"/batches/{batch_id}/ingestion-report"
    )

    assert report.status_code == 200

    body = report.json()

    assert body["batch_id"] == batch_id
    assert body["available"] is True
    assert body["total_records"] > 0


def test_run_batch():
    response = client.post(
        "/batches",
        json={
            "name": "Pipeline API Test",
            "scenario": "NORMAL",
            "seed": 42,
            "num_cases": 5,
        },
    )

    assert response.status_code == 200

    batch_id = response.json()["batch_id"]

    run_response = client.post(
        f"/batches/{batch_id}/run"
    )

    assert run_response.status_code == 200

    body = run_response.json()

    assert body["batch"]["batch_id"] == batch_id
    assert body["batch"]["status"] == "COMPLETED"
    assert body["pipeline"]["status"] == "COMPLETED"

    assert (
        body["pipeline"]["total_duration_ms"]
        >= 0
    )


def test_run_batch_is_idempotent_after_completion():
    create = client.post(
        "/batches",
        json={
            "name": "Idempotent Test",
            "scenario": "NORMAL",
            "seed": 99,
            "num_cases": 5,
        },
    )

    batch_id = create.json()["batch_id"]

    first = client.post(
        f"/batches/{batch_id}/run"
    )

    second = client.post(
        f"/batches/{batch_id}/run"
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert (
        second.json()["message"]
        == "Batch already completed."
    )