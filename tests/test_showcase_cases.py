"""Known-answer business scenarios, source lineage and reproducible artifacts."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from eq_proof.controls import CATALOGUE, analyze, load_csv, load_equations, parse_xer
from eq_proof.controls_cli import main as controls_cli

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "close_walkthrough"
WEB = ROOT / "src" / "eq_proof" / "web" / "showcase-cases.json"


def load_generator():
    specification = importlib.util.spec_from_file_location("showcase_generator", ROOT / "scripts" / "regenerate_showcase_cases.py")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


@pytest.mark.parametrize("case_id,gate,blockers,failures,exit_status", [
    ("blocked", "blocked", 3, 5, 3),
    ("review", "review", 0, 2, 0),
    ("ready", "ready", 0, 0, 0),
])
def test_real_cli_sources_produce_known_close_states(tmp_path, case_id, gate, blockers, failures, exit_status):
    fixture = FIXTURES / case_id
    output = tmp_path / case_id
    status = controls_cli([
        "analyze", "--p6-xer", str(fixture / "schedule.xer"),
        "--cost-csv", str(fixture / "cost.csv"),
        "--equations", str(fixture / "custom_equations.json"),
        "--currency", "USD", "--output", str(output),
    ])
    assert status == exit_status
    room = json.loads((output / "control-room.json").read_text(encoding="utf-8"))
    assert room["gate"]["status"] == gate
    assert room["gate"]["blockers"] == blockers
    assert room["gate"]["failures"] == failures
    assert room["analysis"]["equations_executed"] == 32
    assert room["analysis"]["summary"]["not_applicable"] == 1
    assert room["portfolio"]["defensible_eac"] == 418_000_000
    assert room["portfolio"]["configured_change_and_risk"] == 65_000_000
    assert room["portfolio"]["reconstructed_risk_adjusted_eac"] == 483_000_000
    assert room["portfolio"]["deterministic_forecast_gap"] == (11_000_000 if case_id == "blocked" else 0)
    case = next(item for item in json.loads(WEB.read_text(encoding="utf-8"))["cases"] if item["id"] == case_id)
    published = json.loads((ROOT / "evidence" / "close-walkthrough" / case_id / "control-room.json").read_text(encoding="utf-8"))
    assert published["demo"] == {
        "name": case["title"], "description": case["description"],
        "synthetic": True, "showcase_case": case_id,
    }
    assert published == case["control_room"]
    # The published workspace adds presentation provenance without altering CLI results.
    assert {key: value for key, value in published.items() if key != "demo"} == room
    findings = room["analysis"]["findings"]
    authorization = [item for item in findings if item["equation_id"] == "portfolio.board_authorization"]
    assert len(authorization) == 3
    assert {item["status"] for item in authorization} == {"pass"}
    not_applicable = [item for item in findings if item["status"] == "not_applicable"]
    assert [(item["record_id"], item["equation_id"]) for item in not_applicable] == [
        ("COM-A300", "schedule.progress_duration"),
    ]
    if case_id == "review":
        assert {item["domain"] for item in room["exceptions"]} == {"schedule"}
        # Historical compatibility field means no blockers, not the final gate.
        assert room["analysis"]["close_ready"] is True
        assert controls_cli([
            "analyze", "--p6-xer", str(fixture / "schedule.xer"),
            "--cost-csv", str(fixture / "cost.csv"),
            "--equations", str(fixture / "custom_equations.json"),
            "--output", str(tmp_path / "strict"), "--fail-on", "minor",
        ]) == 3
    assert set(path.name for path in output.iterdir()) == {"analysis.json", "control-room.json", "report.md", "exceptions.csv"}


def test_showcase_artifacts_match_deterministic_regeneration():
    generated = load_generator().build_artifacts()
    assert len(generated) == 13
    for relative, expected in generated.items():
        assert (ROOT / relative).read_bytes() == expected, str(relative)
        assert b"\r" not in expected, str(relative)


def test_browser_source_copies_hash_exact_native_input_bytes():
    manifest = json.loads(WEB.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "eq-proof/showcase-cases@1"
    assert [case["id"] for case in manifest["cases"]] == ["blocked", "review", "ready"]
    for case in manifest["cases"]:
        assert case["synthetic"] is True
        assert case["currency"] == "USD"
        assert {source["kind"] for source in case["source_files"]} == {"p6_xer", "cost_csv", "equation_pack"}
        for source in case["source_files"]:
            assert Path(source["name"]).name == source["name"]
            raw = (FIXTURES / case["id"] / source["name"]).read_bytes()
            assert source["content"].encode("utf-8") == raw
            assert source["sha256"] == hashlib.sha256(raw).hexdigest()
        for source in case["control_room"]["analysis"]["source_manifest"]:
            assert source["sha256"] == next(item["sha256"] for item in case["source_files"] if item["name"] == source["name"])


def test_missing_authority_is_visible_as_unexecuted_and_does_not_prove_approval():
    fixture = FIXTURES / "ready"
    records = [*parse_xer(fixture / "schedule.xer"), *load_csv(fixture / "cost.csv")]
    for record in records:
        record.pop("delegated_authorization", None)
    result = analyze(records, equations=[*CATALOGUE, *load_equations(fixture / "custom_equations.json")])
    authorization = [item for item in result.findings if item.equation_id == "portfolio.board_authorization"]
    assert {item.status for item in authorization} == {"not_applicable"}
    assert result.gate_status == "ready"
    assert result.equations_executed == 29
