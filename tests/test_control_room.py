import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import eq_proof.control_room as room_module
import eq_proof.webapp as webapp
from eq_proof.control_room import CONTROL_ROOM_SCHEMA, build_control_room
from eq_proof.controls import CATALOGUE, Equation, analyze, load_csv, parse_xer
from eq_proof.webapp import create_app

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "hyperscale_close"


def fixture_result():
    records = [
        *parse_xer(FIXTURE / "schedule.xer"),
        *load_csv(FIXTURE / "cost.csv"),
    ]
    return records, analyze(records, sources=("schedule.xer", "cost.csv"))


def test_portfolio_states_are_separate_and_semantically_named():
    records, analysis = fixture_result()
    room = build_control_room(records, analysis, currency="CAD")
    assert room["schema_version"] == CONTROL_ROOM_SCHEMA == "eq-proof/control-room@2"
    assert room["units"]["currency"] == "CAD"
    assert room["portfolio"] == {
        "accounts_reconstructed": 3,
        "reported_eac": 407_000_000,
        "defensible_eac": 418_000_000,
        "deterministic_forecast_gap": 11_000_000,
        "configured_change_and_risk": 65_000_000,
        "submitted_risk_adjusted_eac": 472_000_000,
        "reconstructed_risk_adjusted_eac": 483_000_000,
        "risk_adjusted_reconciliation_gap": 11_000_000,
        "risk_adjusted_summary_coverage": {
            "submitted_accounts": 3,
            "reconstructed_accounts": 3,
            "complete": True,
        },
        "exposure_above_reported_eac": 76_000_000,
    }
    assert room["assurance"]["calibrated_probability"] is False
    assert "P80" not in room["gate"]["headline"]


def test_incomplete_submitted_risk_summary_is_not_fabricated():
    records = [
        {
            "record_id": "A",
            "AC": 4,
            "ETC": 6,
            "EAC": 9,
            "pending_change_exposure": 1,
            "risk_exposure": 2,
            "risk_adjusted_EAC": 12,
        },
        {
            "record_id": "B",
            "AC": 5,
            "ETC": 5,
            "EAC": 10,
            "pending_change_exposure": 0,
            "risk_exposure": 1,
        },
    ]
    portfolio = build_control_room(records, analyze(records, equations=[]))["portfolio"]
    assert portfolio["submitted_risk_adjusted_eac"] is None
    assert portfolio["risk_adjusted_reconciliation_gap"] is None
    assert portfolio["risk_adjusted_summary_coverage"]["complete"] is False


def test_review_and_ready_gate_labels():
    major = Equation("m", "m", "custom", "x == 1", "major", "", "fix", ("x",))
    review = analyze([{"record_id": "A", "x": 2}], equations=[major])
    ready = analyze([{"record_id": "A", "x": 1}], equations=[major])
    assert build_control_room([], review)["gate"]["label"] == "REVIEW REQUIRED"
    assert build_control_room([], ready)["gate"]["label"] == "CLOSE READY"
    with pytest.raises(ValueError, match="currency"):
        build_control_room([], ready, currency="dollars")


def test_schedule_findings_affect_schedule_assurance_not_money():
    records, analysis = fixture_result()
    graph = build_control_room(records, analysis)["graph"]
    schedule_edges = [
        edge
        for edge in graph["edges"]
        if "schedule." in edge["source"] and edge["relation"] == "affects"
    ]
    assert schedule_edges
    assert {edge["target"] for edge in schedule_edges} == {"assurance:schedule"}


def test_graph_reports_truncation(monkeypatch):
    monkeypatch.setattr(room_module, "GRAPH_MAX_ACCOUNTS", 1)
    monkeypatch.setattr(room_module, "GRAPH_MAX_FINDINGS", 1)
    records = [
        {"record_id": "A", "AC": 1, "ETC": 1, "EAC": 1},
        {"record_id": "B", "AC": 1, "ETC": 1, "EAC": 1},
    ]
    limits = build_control_room(records, analyze(records))["graph"]["limits"]
    assert limits["truncated"] is True
    assert limits["accounts_shown"] == 1
    assert limits["findings_shown"] == 1


def test_web_health_security_demo_and_validation():
    client = TestClient(create_app())
    health = client.get("/api/health")
    assert health.json() == {"status": "ok", "mode": "local-first"}
    assert "default-src 'self'" in health.headers["content-security-policy"]
    assert health.headers["x-frame-options"] == "DENY"
    assert client.get("/").status_code == 200
    assert client.get("/api/demo").json()["schema_version"] == "eq-proof/control-room@2"
    good = client.post(
        "/api/equations/validate",
        json={
            "id": "custom.cap",
            "expression": "EAC <= cap",
            "required_fields": ["EAC", "cap"],
        },
    )
    assert good.status_code == 200
    assert good.json()[0]["id"] == "custom.cap"
    bad = client.post(
        "/api/equations/validate",
        json={
            "id": "custom.bad",
            "expression": "__import__('os') == 1",
            "required_fields": ["x"],
        },
    )
    assert bad.status_code == 400


def test_web_upload_selection_currency_and_errors(monkeypatch):
    client = TestClient(create_app())
    content = (
        "record_id,AC,ETC,EAC,pending_change_exposure,risk_exposure\n"
        "CA,40,70,100,5,8\n"
    )
    response = client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", content, "text/csv")},
        data={
            "custom_equations": "[]",
            "catalogue_ids": "cost.eac_identity",
            "currency": "CAD",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["units"]["currency"] == "CAD"
    assert payload["portfolio"]["deterministic_forecast_gap"] == 10
    assert payload["portfolio"]["exposure_above_reported_eac"] == 23

    no_catalogue = client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", content, "text/csv")},
        data={"custom_equations": "[]", "catalogue_ids": "", "currency": "USD"},
    ).json()
    assert no_catalogue["analysis"]["equations_considered"] == 0
    assert no_catalogue["gate"]["status"] == "ready"

    unknown = client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", content, "text/csv")},
        data={"custom_equations": "[]", "catalogue_ids": "unknown"},
    )
    assert unknown.status_code == 400
    assert client.post("/api/analyze", data={"custom_equations": "[]"}).status_code == 400
    assert client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", content, "text/csv")},
        data={"custom_equations": "bad"},
    ).status_code == 400
    assert client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", content, "text/csv")},
        data={"custom_equations": "[]", "currency": "dollars"},
    ).status_code == 400
    monkeypatch.setattr(webapp, "MAX_UPLOAD_BYTES", 1)
    assert client.post(
        "/api/analyze",
        files={"cost_csv": ("cost.csv", content, "text/csv")},
        data={"custom_equations": "[]"},
    ).status_code == 400


def test_trusted_host_rejects_non_loopback():
    client = TestClient(create_app(), base_url="http://evil.example")
    assert client.get("/api/health").status_code == 400


def test_demo_payload_matches_semantic_contract():
    payload = json.loads(
        (ROOT / "src" / "eq_proof" / "web" / "demo-data.json").read_text()
    )
    assert payload["portfolio"]["deterministic_forecast_gap"] == 11_000_000
    assert payload["portfolio"]["exposure_above_reported_eac"] == 76_000_000
    assert payload["assurance"]["calibrated_probability"] is False
    assert len(payload["catalogue"]) == len(CATALOGUE)


def test_control_room_defensive_paths_and_domain_impacts():
    records = [
        {"record_id": "A", "EAC": "bad", "AC": 1, "ETC": 2},
        {"record_id": "B", "EAC": 3},
    ]
    equations = [
        Equation("risk", "risk", "risk", "x == 1", "major", "", "fix", ("x",)),
        Equation("ev", "ev", "earned_value", "x == 1", "major", "", "fix", ("x",)),
        Equation("other", "other", "custom", "x == 1", "info", "", "fix", ("x",)),
    ]
    room = build_control_room(
        records,
        analyze([{"record_id": "X", "x": 2}], equations=equations),
    )
    targets = {
        edge["target"]
        for edge in room["graph"]["edges"]
        if edge["relation"] == "affects"
    }
    assert {"metric:risk_reconciliation", "assurance:earned_value", "decision:gate"} <= targets
    assert room["portfolio"]["accounts_reconstructed"] == 2


def test_web_additional_resource_limits_and_missing_demo(monkeypatch, tmp_path):
    client = TestClient(create_app())
    monkeypatch.setattr(webapp, "MAX_INLINE_EQUATION_BYTES", 1)
    assert client.post("/api/equations/validate", content=b"[]").status_code == 400
    monkeypatch.setattr(webapp, "MAX_INLINE_EQUATION_BYTES", 256 * 1024)
    monkeypatch.setattr(webapp, "MAX_UPLOAD_FILES", 1)
    files = [
        ("cost_csv", ("a.csv", "record_id,EAC\nA,1\n", "text/csv")),
        ("cost_csv", ("b.csv", "record_id,EAC\nB,1\n", "text/csv")),
    ]
    assert client.post(
        "/api/analyze",
        files=files,
        data={"custom_equations": "[]"},
    ).status_code == 400
    monkeypatch.setattr(webapp, "WEB_ROOT", tmp_path)
    assert client.get("/api/demo").status_code == 503
