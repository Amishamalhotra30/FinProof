from decimal import Decimal

from fastapi.testclient import TestClient

from app.api.decision import store
from app.main import app
from app.verification.models import (
    ControlCheck,
    ControlStatus,
    ExpectedFinancialState,
    VerificationResult,
    VerificationStatus,
)


client = TestClient(app)


def setup_function():
    store.clear()


def make_verified_result(
    case_id: str = "CASE_001",
) -> VerificationResult:
    return VerificationResult(
        case_id=case_id,
        status=VerificationStatus.VERIFIED,
        observed_state={
            "gross_captured": Decimal("1000"),
            "total_refunded": Decimal("0"),
            "total_fees": Decimal("0"),
            "total_adjustments": Decimal("0"),
            "expected_settlement": Decimal("1000"),
            "total_bank_credit": Decimal("1000"),
        },
        expected_state=ExpectedFinancialState(
            gross_captured=Decimal("1000"),
            total_refunded=Decimal("0"),
            total_fees=Decimal("0"),
            total_adjustments=Decimal("0"),
            expected_settlement=Decimal("1000"),
        ),
        controls=[
            ControlCheck(
                control_id="SETTLEMENT_AMOUNT",
                control_name="Settlement Amount",
                status=ControlStatus.PASS,
            )
        ],
        discrepancies=[],
    )


# ============================================================
# BASIC ROUTE / NOT FOUND TESTS
# ============================================================


def test_unknown_decision_returns_404():
    response = client.get(
        "/cases/CASE_UNKNOWN/decision"
    )

    assert response.status_code == 404


def test_decision_for_unknown_case_returns_404():
    response = client.post(
        "/cases/CASE_UNKNOWN/decision"
    )

    assert response.status_code == 404


def test_unknown_workflow_returns_404():
    response = client.get(
        "/cases/CASE_UNKNOWN/workflow"
    )

    assert response.status_code == 404


def test_unknown_audit_returns_404():
    response = client.get(
        "/cases/CASE_UNKNOWN/audit"
    )

    assert response.status_code == 404


def test_unknown_review_package_returns_404():
    response = client.get(
        "/cases/CASE_UNKNOWN/review-package"
    )

    assert response.status_code == 404


# ============================================================
# DECISION CREATION
# ============================================================


def test_decision_can_be_created_for_verified_case():
    verification = make_verified_result(
        "CASE_001"
    )

    store.register_verification(
        verification
    )

    response = client.post(
        "/cases/CASE_001/decision"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["case_id"] == "CASE_001"
    assert body["decision"] == "AUTO_RESOLVED"
    assert body["reason_code"] == "ALL_CONTROLS_PASSED"
    assert body["workflow_state"] == "AUTO_RESOLVED"
    assert body["action"]["action_type"] == (
        "MARK_RESOLVED"
    )
    assert body["audit_entry_id"] is not None


def test_decision_can_be_retrieved():
    verification = make_verified_result(
        "CASE_002"
    )

    store.register_verification(
        verification
    )

    create_response = client.post(
        "/cases/CASE_002/decision"
    )

    assert create_response.status_code == 200

    response = client.get(
        "/cases/CASE_002/decision"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["case_id"] == "CASE_002"
    assert body["decision"] == "AUTO_RESOLVED"
    assert body["reason_code"] == (
        "ALL_CONTROLS_PASSED"
    )


def test_decision_exposes_required_fields():
    verification = make_verified_result(
        "CASE_003"
    )

    store.register_verification(
        verification
    )

    response = client.post(
        "/cases/CASE_003/decision"
    )

    assert response.status_code == 200

    body = response.json()

    expected_fields = {
        "case_id",
        "decision",
        "reason_code",
        "basis",
        "financial_impact",
        "materiality",
        "policy_rule_id",
        "evidence_sufficient",
        "investigation_validated",
        "contradictory_evidence",
        "supporting_evidence_ids",
        "decision_timestamp",
        "workflow_state",
        "action",
        "audit_entry_id",
    }

    assert expected_fields <= set(
        body.keys()
    )


# ============================================================
# WORKFLOW
# ============================================================


def test_workflow_is_exposed_after_decision():
    verification = make_verified_result(
        "CASE_004"
    )

    store.register_verification(
        verification
    )

    decision_response = client.post(
        "/cases/CASE_004/decision"
    )

    assert decision_response.status_code == 200

    response = client.get(
        "/cases/CASE_004/workflow"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["case_id"] == "CASE_004"
    assert body["state"] == "AUTO_RESOLVED"
    assert body["decision"] == "AUTO_RESOLVED"
    assert body["review_records"] == []


# ============================================================
# AUDIT
# ============================================================


def test_decision_creates_audit_entry():
    verification = make_verified_result(
        "CASE_005"
    )

    store.register_verification(
        verification
    )

    response = client.post(
        "/cases/CASE_005/decision"
    )

    assert response.status_code == 200

    audit_response = client.get(
        "/cases/CASE_005/audit"
    )

    assert audit_response.status_code == 200

    body = audit_response.json()

    assert body["case_id"] == "CASE_005"
    assert body["count"] == 1
    assert len(body["entries"]) == 1

    entry = body["entries"][0]

    assert entry["case_id"] == "CASE_005"
    assert entry["decision"] == "AUTO_RESOLVED"
    assert entry["reason_code"] == (
        "ALL_CONTROLS_PASSED"
    )
    assert entry["policy_rule_id"] == "P7-R1"


# ============================================================
# REVIEW PACKAGE / HUMAN REVIEW
# ============================================================


def test_review_package_is_rejected_for_auto_resolved_case():
    verification = make_verified_result(
        "CASE_006"
    )

    store.register_verification(
        verification
    )

    response = client.post(
        "/cases/CASE_006/decision"
    )

    assert response.status_code == 200
    assert response.json()["decision"] == (
        "AUTO_RESOLVED"
    )

    package_response = client.get(
        "/cases/CASE_006/review-package"
    )

    assert package_response.status_code == 409


def test_review_requires_existing_decision():
    response = client.post(
        "/cases/CASE_007/review",
        json={
            "action": "APPROVE",
            "comment": "Approved after review.",
            "reviewer_id": "REVIEWER_001",
        },
    )

    assert response.status_code == 400


def test_review_requires_non_empty_comment():
    verification = make_verified_result(
        "CASE_008"
    )

    store.register_verification(
        verification
    )

    client.post(
        "/cases/CASE_008/decision"
    )

    response = client.post(
        "/cases/CASE_008/review",
        json={
            "action": "APPROVE",
            "comment": "",
            "reviewer_id": "REVIEWER_001",
        },
    )

    assert response.status_code == 422


# ============================================================
# ROUTES
# ============================================================


def test_api_exposes_decision_routes():
    response = client.get(
        "/openapi.json"
    )

    assert response.status_code == 200

    paths = set(
        response.json()["paths"].keys()
    )

    expected_paths = {
        "/cases/{case_id}/decision",
        "/cases/{case_id}/review",
        "/cases/{case_id}/workflow",
        "/cases/{case_id}/audit",
        "/cases/{case_id}/review-package",
        "/cases/{case_id}/reinvestigate",
        "/cases/{case_id}/reinvestigate/start",
    }

    assert expected_paths <= paths


# ============================================================
# GROUND-TRUTH SAFETY
# ============================================================


def test_decision_api_does_not_expose_ground_truth():
    verification = make_verified_result(
        "CASE_009"
    )

    store.register_verification(
        verification
    )

    response = client.post(
        "/cases/CASE_009/decision"
    )

    assert response.status_code == 200

    body = response.json()

    assert "ground_truth" not in body
    assert "ground_truth_events" not in body
    assert "ground_truth_relationships" not in body
    assert "ground_truth_hypotheses" not in body


# ============================================================
# STORE ISOLATION
# ============================================================


def test_store_clear_removes_decision_state():
    verification = make_verified_result(
        "CASE_010"
    )

    store.register_verification(
        verification
    )

    response = client.post(
        "/cases/CASE_010/decision"
    )

    assert response.status_code == 200

    store.clear()

    decision_response = client.get(
        "/cases/CASE_010/decision"
    )

    assert decision_response.status_code == 404


# ============================================================
# TERMINAL STATE PROTECTION
# ============================================================


def test_repeated_decision_is_rejected_after_terminal_state():
    verification = make_verified_result(
        "CASE_011"
    )

    store.register_verification(
        verification
    )

    first = client.post(
        "/cases/CASE_011/decision"
    )

    second = client.post(
        "/cases/CASE_011/decision"
    )

    assert first.status_code == 200
    assert first.json()["decision"] == (
        "AUTO_RESOLVED"
    )

    assert second.status_code == 400