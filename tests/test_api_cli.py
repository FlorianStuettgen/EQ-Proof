import json
from pathlib import Path

from eq_proof import prove_document, repair_document, verify_document
from eq_proof.cli import EXIT_CONSTRAINT_VIOLATION, main

ROOT = Path(__file__).resolve().parents[1]


def documents():
    example = ROOT / "examples" / "portfolio_allocation"
    return (
        json.loads((example / "spec.json").read_text()),
        json.loads((example / "input.json").read_text()),
    )


def test_high_level_api_round_trip():
    spec, values = documents()
    result = repair_document(spec, values)
    assert result.repaired["forecast_c"] == 0.2
    proof = prove_document(spec, values, created_utc="2026-01-01T00:00:00Z")
    assert verify_document(proof).verified


def test_cli_validate_repair_and_verify_round_trip(tmp_path, capsys):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    proof = tmp_path / "proof.json"
    report = tmp_path / "proof.md"
    spec = ROOT / "examples/portfolio_allocation/spec.json"
    values = ROOT / "examples/portfolio_allocation/input.json"

    assert main(["validate", "--spec", str(spec), "--input", str(values)]) == EXIT_CONSTRAINT_VIOLATION
    assert "VIOLATION" in capsys.readouterr().out
    assert main(["keygen", "--private-key", str(private_key), "--public-key", str(public_key)]) == 0
    assert main(
        [
            "repair",
            "--spec",
            str(spec),
            "--input",
            str(values),
            "--proof",
            str(proof),
            "--report",
            str(report),
            "--private-key",
            str(private_key),
        ]
    ) == 0
    assert main(["verify", str(proof), "--public-key", str(public_key)]) == 0
    output = capsys.readouterr().out
    assert "semantics=pass" in output
    assert json.loads(proof.read_text())["result"]["status"] == "repaired"
    assert "semantic replay" in report.read_text()


def test_cli_reports_bad_json_without_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("{")
    spec = ROOT / "examples/portfolio_allocation/spec.json"
    assert main(["validate", "--spec", str(spec), "--input", str(bad)]) == 2
    assert "error" in capsys.readouterr().err


def test_cli_json_validate_feasible_and_integrity_only(tmp_path, capsys):
    spec = ROOT / "examples/portfolio_allocation/spec.json"
    feasible_input = tmp_path / "feasible.json"
    feasible_input.write_text(json.dumps({"forecast_a": 0.5, "forecast_b": 0.3, "forecast_c": 0.2}))
    assert main(["validate", "--spec", str(spec), "--input", str(feasible_input), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["feasible"] is True

    proof_path = tmp_path / "proof.json"
    assert main([
        "repair", "--spec", str(spec), "--input", str(feasible_input), "--proof", str(proof_path)
    ]) == 0
    assert main(["verify", str(proof_path), "--integrity-only"]) == 0
    assert "semantics=skipped" in capsys.readouterr().out


def test_cli_keygen_overwrite_error_and_force(tmp_path, capsys):
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    args = ["keygen", "--private-key", str(private_key), "--public-key", str(public_key)]
    assert main(args) == 0
    assert main(args) == 2
    assert "error" in capsys.readouterr().err
    assert main(args + ["--force"]) == 0
