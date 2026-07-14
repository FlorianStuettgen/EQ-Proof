import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from eq_proof.control_room import CONTROL_ROOM_SCHEMA, build_control_room
from eq_proof.controls import CATALOGUE, analyze, load_csv, parse_xer
from eq_proof.webapp import create_app

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "hyperscale_close"


def fixture_result():
    records = [*parse_xer(FIXTURE / "schedule.xer"), *load_csv(FIXTURE / "cost.csv")]
    return records, analyze(records, sources=("schedule.xer", "cost.csv"))


def test_portfolio_reconstruction_exposes_76m_surprise():
    records, analysis = fixture_result()
    room = build_control_room(records, analysis)
    assert room["schema_version"] == CONTROL_ROOM_SCHEMA
    assert room["gate"]["status"] == "blocked"
    assert room["portfolio"] == pytest.approx(
        {
            "accounts_reconstructed": 3,
            "reported_eac": 407_000_000,
            "defensible_eac": 418_000_000,
            "submitted_p80": 472_000_000,
            "defensible_p80": 483_000_000,
            "deterministic_gap": 11_000_000,
            "risk_adjustment_gap": 11_000_000,
            "hidden_exposure": 76_000_000,
            "quantified_change_and_risk": 65_000_000,
        }
    )
    assert room["surprise"]["contributions"][0]["record_id"] == "MEP-200"
    assert any(node["kind"] == "finding" for node in room["graph"]["nodes"])


def test_control_room_api_serves_demo_catalogue_and_security_headers():
    client = TestClient(create_app())
    health = client.get("/api/health")
    assert health.json() == {"status": "ok", "mode": "local-first"}
    assert "default-src 'self'" in health.headers["content-security-policy"]
    catalogue = client.get("/api/catalogue").json()
    assert len(catalogue) == len(CATALOGUE)
    demo = client.get("/api/demo")
    assert demo.status_code == 200
    assert demo.json()["portfolio"]["hidden_exposure"] == 76_000_000
    assert client.get("/").status_code == 200


def test_upload_api_runs_real_cost_analysis():
    client = TestClient(create_app())
    content = (
        "control_account_id,AC,ETC,EAC,pending_change_exposure,risk_exposure\n"
        "CA-1,40,70,100,5,8\n"
    )
    response = client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", content, "text/csv")},
        data={"custom_equations": "[]", "catalogue_ids": "cost.eac_identity"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["gate"]["status"] == "blocked"
    assert payload["portfolio"]["hidden_exposure"] == 23
    assert payload["exceptions"][0]["equation_id"] == "cost.eac_identity"


def test_upload_api_rejects_missing_files_and_bad_custom_json():
    client = TestClient(create_app())
    assert client.post("/api/analyze", data={"custom_equations": "[]"}).status_code == 400
    response = client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", "control_account_id,EAC\nCA,1\n", "text/csv")},
        data={"custom_equations": "not-json"},
    )
    assert response.status_code == 400


def test_demo_payload_is_deterministic_and_contains_catalogue():
    payload = json.loads((ROOT / "src" / "eq_proof" / "web" / "demo-data.json").read_text())
    assert payload["demo"]["name"].startswith("Hyperscale")
    assert len(payload["catalogue"]) >= 10
