import csv
import json

import pytest

import eq_proof.controls as controls
from eq_proof.controls import (
    CATALOGUE,
    ControlsError,
    Equation,
    analyze,
    evaluate,
    load_csv,
    load_equations,
    normalize_row,
    parse_equations,
    parse_xer,
    validate_equation_set,
    write_outputs,
)
from eq_proof.controls_cli import build_parser, main


def test_evaluate_supported_math_and_comparisons():
    assert evaluate("EAC == AC + ETC", {"EAC": 12, "AC": 5, "ETC": 7}, 0) == (True, 0)
    assert evaluate("max(a, b) <= 5", {"a": 3, "b": 4}, 0)[0]
    assert evaluate("abs(a-b) < 2", {"a": 3, "b": 4}, 0)[0]
    assert evaluate("round(a, 1) >= 1.2", {"a": 1.24}, 0)[0]
    assert not evaluate("a > b", {"a": 4, "b": 4}, 0)[0]


@pytest.mark.parametrize("expression", [
    "__import__('os').system('x') == 0",
    "a ** 2 == 1",
    "a and b",
    "a + b",
    "a < b < c",
    "'x' == 1",
    "abs() == 0",
    "round(a, 1, 2) == 1",
])
def test_evaluate_rejects_unsafe_or_invalid_syntax(expression):
    with pytest.raises(ControlsError):
        evaluate(expression, {"a": 1, "b": 2, "c": 3}, 0)


def test_evaluate_rejects_bad_tolerance_and_zero_division():
    with pytest.raises(ControlsError, match="non-negative"):
        evaluate("a == 1", {"a": 1}, -1)
    with pytest.raises(ZeroDivisionError):
        evaluate("a / b == 1", {"a": 1, "b": 0}, 0)


def test_aliases_distinguish_bac_from_current_budget():
    row = normalize_row({"current_budget": "10", "p80_eac": "12"})
    assert "BAC" not in row
    assert row["risk_adjusted_EAC"] == "12"
    assert row["P80_EAC"] == "12"


def test_csv_loader_maps_aliases_hashes_and_rejects_empty(tmp_path):
    source = tmp_path / "cost.csv"
    source.write_text("control_account_id,actual_cost,estimate_to_complete,forecast_at_completion\nCA-1,4,7,10\n")
    rows = load_csv(source)
    assert rows[0]["AC"] == "4"
    assert rows[0]["record_id"] == "CA-1"
    assert rows[0]["_source"] == "cost.csv"
    assert len(rows[0]["_source_sha256"]) == 64
    empty = tmp_path / "empty.csv"
    empty.write_text("a,b\n")
    with pytest.raises(ControlsError, match="data rows"):
        load_csv(empty)
    no_header = tmp_path / "no-header.csv"
    no_header.write_text("")
    with pytest.raises(ControlsError, match="header"):
        load_csv(no_header)
    with pytest.raises(ControlsError, match="record type"):
        load_csv(source, "bad")


def test_csv_and_xer_safety_limits(tmp_path, monkeypatch):
    csv_path = tmp_path / "many.csv"
    csv_path.write_text("record_id,EAC\na,1\nb,2\n")
    monkeypatch.setattr(controls, "MAX_CSV_ROWS", 1)
    with pytest.raises(ControlsError, match="row safety"):
        load_csv(csv_path)
    xer = tmp_path / "many.xer"
    xer.write_text("%T\tTASK\n%F\ttask_id\ttask_code\n%R\t1\tA\n%R\t2\tB\n")
    monkeypatch.setattr(controls, "MAX_XER_ROWS", 1)
    with pytest.raises(ControlsError, match="activity safety"):
        parse_xer(xer)


def test_xer_parser_and_catalogue_applicability(tmp_path):
    xer = tmp_path / "sample.xer"
    xer.write_text(
        "ERMHDR\t23.12\n%T\tTASK\n"
        "%F\ttask_id\ttask_code\tstatus_code\tremain_drtn_hr_cnt\ttotal_float_hr_cnt\n"
        "%R\t1\tA100\tTK_Active\t0\t-1200\n"
        "%R\t2\tA200\tTK_Complete\t0\t20\n"
    )
    rows = parse_xer(xer)
    result = analyze(rows)
    failed = {item.equation_id for item in result.failures}
    assert "schedule.progress_duration" in failed
    assert "schedule.extreme_negative_float" in failed
    completed = [item for item in result.findings if item.record_id == "A200" and item.equation_id == "schedule.progress_duration"]
    assert completed[0].status == "not_applicable"
    bad = tmp_path / "bad.xer"
    bad.write_text("ERMHDR\t23.12\n")
    with pytest.raises(ControlsError, match="TASK"):
        parse_xer(bad)


def valid_equation(**overrides):
    item = {
        "id": "custom.cap",
        "title": "Cap",
        "domain": "governance",
        "expression": "EAC <= authorization",
        "severity": "blocker",
        "required_fields": ["EAC", "authorization"],
        "record_type": "control_account",
    }
    item.update(overrides)
    return item


def test_equation_pack_validation_and_applicability(tmp_path):
    equation = parse_equations([valid_equation(applies_when={"field": "status", "contains_any": ["open"]})])[0]
    assert equation.applicability_field == "status"
    path = tmp_path / "pack.json"
    path.write_text(json.dumps([valid_equation()]))
    assert load_equations(path)[0].id == "custom.cap"
    invalid = [
        {}, valid_equation(extra=True), valid_equation(id="bad id"),
        valid_equation(required_fields=[]), valid_equation(required_fields=["EAC"]),
        valid_equation(required_fields=["EAC", "EAC"]), valid_equation(required_fields=["for"]),
        valid_equation(severity="critical"), valid_equation(record_type="portfolio"),
        valid_equation(tolerance=-1), valid_equation(applies_when={"field": "status"}),
    ]
    for document in invalid:
        with pytest.raises(ControlsError):
            parse_equations([document])
    with pytest.raises(ControlsError, match="array"):
        parse_equations({})
    with pytest.raises(ControlsError, match="Duplicate"):
        parse_equations([valid_equation(), valid_equation()])


def test_equation_set_rejects_duplicate_and_missing_fields():
    equation = Equation("x", "x", "custom", "a == b", "major", "", "fix", ("a",))
    with pytest.raises(ControlsError, match="missing"):
        validate_equation_set([equation])
    good = Equation("x", "x", "custom", "a == 1", "major", "", "fix", ("a",))
    with pytest.raises(ControlsError, match="Duplicate"):
        validate_equation_set([good, good])


def test_analysis_gate_states_thresholds_and_manifest():
    blocker = Equation("b", "b", "custom", "x == 1", "blocker", "", "fix", ("x",))
    major = Equation("m", "m", "custom", "x == 1", "major", "", "fix", ("x",))
    ready = analyze([{"record_id": "A", "x": 1}], equations=[major])
    review = analyze([{"record_id": "A", "x": 2}], equations=[major])
    blocked = analyze([{"record_id": "A", "x": 2}], equations=[blocker])
    assert ready.gate_status == "ready"
    assert review.gate_status == "review"
    assert blocked.gate_status == "blocked"
    assert review.fails_at_or_above("major")
    assert not review.fails_at_or_above("blocker")
    assert not review.fails_at_or_above("never")
    with pytest.raises(ControlsError, match="threshold"):
        review.fails_at_or_above("bad")
    assert review.to_dict()["equations"][0]["id"] == "m"


def test_nonfinite_results_are_json_safe_and_exports_neutralize_formula(tmp_path):
    equation = Equation("ratio", "ratio", "custom", "x / y == 1", "major", "", "=HYPERLINK('x')", ("x", "y"))
    result = analyze([{"record_id": "=2+2", "x": 1, "y": 0}], equations=[equation])
    finding = result.to_dict()["findings"][0]
    assert finding["residual"] is None
    assert finding["residual_state"] == "non_finite"
    out = tmp_path / "out"
    write_outputs(result, out)
    json.loads((out / "analysis.json").read_text())
    rows = list(csv.reader((out / "exceptions.csv").open()))
    assert rows[1][2].startswith("'")
    assert rows[1][-1].startswith("'")
    assert "non-finite" in (out / "report.md").read_text()


def test_cli_outputs_control_room_and_failure_thresholds(tmp_path, capsys):
    source = tmp_path / "cost.csv"
    source.write_text("record_id,AC,ETC,EAC\nCA,40,70,100\n")
    out = tmp_path / "out"
    assert main(["analyze", "--cost-csv", str(source), "--output", str(out), "--currency", "CAD"]) == 3
    room = json.loads((out / "control-room.json").read_text())
    assert room["units"]["currency"] == "CAD"
    assert room["gate"]["status"] == "blocked"
    assert main(["analyze", "--cost-csv", str(source), "--output", str(tmp_path / "never"), "--fail-on", "never"]) == 0
    assert main(["analyze", "--output", str(tmp_path / "none")]) == 2
    assert main(["analyze", "--cost-csv", str(source), "--output", str(tmp_path / "bad"), "--currency", "dollar"]) == 2
    capsys.readouterr()
    assert main(["catalogue", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)[0]["id"]


def test_cli_host_is_loopback_only():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["serve", "--host", "0.0.0.0"])


def test_catalogue_domains_and_risk_boundary():
    assert {"cost", "earned_value", "change", "risk", "schedule"} <= {item.domain for item in CATALOGUE}
    risk = next(item for item in CATALOGUE if item.id == "risk.adjusted_bridge")
    assert "does not calculate a statistical P80" in risk.description


def test_defensive_numeric_expression_and_pack_limits(monkeypatch):
    for value in (True, object(), float("inf")):
        with pytest.raises(ControlsError):
            controls._number(value, "value")
    for expression in ("", "a + == 1", "a == 'x'", "round(a, digits=1) == 1", "min() == 1"):
        with pytest.raises(ControlsError):
            evaluate(expression, {"a": 1}, 0)
    with pytest.raises(KeyError):
        evaluate("missing == 1", {}, 0)
    monkeypatch.setattr(controls, "MAX_EXPRESSION_LENGTH", 3)
    with pytest.raises(ControlsError, match="character limit"):
        evaluate("long == 1", {"long": 1}, 0)
    monkeypatch.setattr(controls, "MAX_EXPRESSION_LENGTH", 4096)
    monkeypatch.setattr(controls, "MAX_EXPRESSION_NODES", 1)
    with pytest.raises(ControlsError, match="complex"):
        evaluate("a == 1", {"a": 1}, 0)
    monkeypatch.setattr(controls, "MAX_EQUATIONS", 0)
    with pytest.raises(ControlsError, match="equation limit"):
        parse_equations([valid_equation()])
    with pytest.raises(ControlsError, match="Analysis exceeds"):
        validate_equation_set([Equation("x", "x", "custom", "a == 1", "major", "", "fix", ("a",))])


def test_additional_equation_document_errors():
    bad_documents = [
        [1],
        [{"id": "x", "expression": 1, "required_fields": ["x"]}],
        [{"id": "x", "expression": "x == 1", "required_fields": "x"}],
        [valid_equation(applies_when={"field": "", "contains_any": ["x"]})],
        [valid_equation(applies_when={"field": "status", "contains_any": []})],
        [valid_equation(title="")],
    ]
    for document in bad_documents:
        with pytest.raises(ControlsError):
            parse_equations(document)
    invalid_severity = Equation("x", "x", "custom", "a == 1", "critical", "", "fix", ("a",))
    with pytest.raises(ControlsError, match="severity"):
        validate_equation_set([invalid_severity])
    invalid_type = Equation("x", "x", "custom", "a == 1", "major", "", "fix", ("a",), record_type="portfolio")
    with pytest.raises(ControlsError, match="record type"):
        validate_equation_set([invalid_type])


def test_analysis_defaults_source_and_handles_bad_values():
    equation = Equation("x", "x", "custom", "a == 1", "major", "", "fix", ("a",))
    result = analyze([{"_source": "folder/input.csv", "_source_sha256": "abc", "_row": 2, "a": "bad"}], equations=[equation])
    assert result.sources == ("input.csv",)
    assert result.findings[0].status == "not_applicable"
    assert result.source_manifest[0]["sha256"] == "abc"


def test_cli_serve_path_without_opening_browser(monkeypatch):
    import uvicorn
    called = {}
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: called.update(kwargs))
    assert main(["serve", "--no-open", "--host", "localhost", "--port", "9999"]) == 0
    assert called["host"] == "localhost"
    assert called["port"] == 9999
