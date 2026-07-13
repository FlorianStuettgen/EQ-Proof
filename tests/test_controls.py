import json
from pathlib import Path

import pytest

from eq_proof.controls import (
    CATALOGUE,
    ControlsError,
    analyze,
    evaluate,
    load_csv,
    load_equations,
    parse_xer,
)
from eq_proof.controls_cli import main


def test_equation_evaluator_supports_controls_math_and_rejects_calls():
    assert evaluate("EAC == AC + ETC", {"EAC": 12, "AC": 5, "ETC": 7}, 1e-9) == (True, 0)
    passed, residual = evaluate("CPI == EV / AC", {"CPI": .8, "EV": 80, "AC": 100}, 1e-9)
    assert passed and residual == pytest.approx(0)
    with pytest.raises(ControlsError):
        evaluate("__import__('os').system('x') == 0", {}, 1e-9)


def test_cost_csv_auto_maps_aliases_and_ranks_blockers(tmp_path):
    source = tmp_path / "cost.csv"
    source.write_text(
        "control_account_id,budget_at_completion,actual_cost,estimate_to_complete,"
        "forecast_at_completion,variance_at_completion,baseline_budget,approved_changes,current_budget\n"
        "CA-01,100,40,70,105,-5,90,10,105\n"
    )
    result = analyze(load_csv(source))
    ids = {item.equation_id for item in result.failures}
    assert not result.close_ready
    assert "cost.eac_identity" in ids
    assert "change.budget_bridge" in ids


def test_p6_xer_parser_and_schedule_catalogue(tmp_path):
    xer = tmp_path / "sample.xer"
    xer.write_text(
        "ERMHDR\t23.12\t2026-07-13\n"
        "%T\tTASK\n"
        "%F\ttask_id\ttask_code\ttask_name\twbs_id\tstatus_code\tremain_drtn_hr_cnt\ttotal_float_hr_cnt\n"
        "%R\t1\tA1000\tInstall Busway\tWBS1\tTK_Active\t0\t-1200\n"
    )
    rows = parse_xer(xer)
    assert rows[0]["record_id"] == "A1000"
    failed = {item.equation_id for item in analyze(rows).failures}
    assert "schedule.progress_duration" in failed
    assert "schedule.float_reasonable" in failed


def test_user_equation_pack_executes(tmp_path):
    pack = tmp_path / "pack.json"
    pack.write_text(json.dumps([{
        "id": "custom.forecast_cap",
        "title": "Forecast is inside board authorization",
        "domain": "governance",
        "expression": "EAC <= authorization",
        "severity": "blocker",
        "required_fields": ["EAC", "authorization"],
    }]))
    result = analyze([{
        "_record_type": "control_account",
        "record_id": "CA-9",
        "EAC": 120,
        "authorization": 100,
    }], equations=load_equations(pack))
    assert result.failures[0].equation_id == "custom.forecast_cap"


def test_output_package_and_cli(tmp_path):
    cost = tmp_path / "cost.csv"
    cost.write_text("control_account_id,BAC,AC,ETC,EAC,VAC\nCA-1,100,40,60,100,0\n")
    out = tmp_path / "out"
    assert main(["analyze", "--cost-csv", str(cost), "--output", str(out)]) == 0
    assert (out / "analysis.json").exists()
    assert (out / "exceptions.csv").exists()
    assert "Close ready" in (out / "report.md").read_text()
    assert json.loads((out / "analysis.json").read_text())["close_ready"] is True


def test_catalogue_has_multiple_project_controls_domains():
    assert len(CATALOGUE) >= 10
    assert {"cost", "earned_value", "change", "risk", "schedule"} <= {
        item.domain for item in CATALOGUE
    }
