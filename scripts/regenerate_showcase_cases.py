"""Build reproducible, synthetic blocked/review/ready close examples.

Use --check to compare every published artifact without modifying files.
All output uses UTF-8 and LF regardless of the generating platform.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from eq_proof.control_room import build_control_room
from eq_proof.controls import CATALOGUE, analyze, load_csv, load_equations, parse_xer, write_outputs

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "examples" / "close_walkthrough"
WEB_OUTPUT = Path("src/eq_proof/web/showcase-cases.json")
EVIDENCE_OUTPUT = Path("evidence/close-walkthrough")
SOURCE_KINDS = (
    ("schedule.xer", "p6_xer"),
    ("cost.csv", "cost_csv"),
    ("custom_equations.json", "equation_pack"),
)
BOUNDARY = (
    "Synthetic inputs illustrate three deliberately constructed states, not an automated repair "
    "or a real approval. Ready means no failures among selected, applicable equations; it does "
    "not establish completeness, forecast accuracy, schedule feasibility, or authority to close. "
    "The risk bridge is arithmetic, not a calculated P80."
)
APPLICABILITY = (
    "All three supplied authorization limits are checked. One progress-duration check is not "
    "applicable because COM-A300 has not started. Missing required fields in other data can "
    "also produce not-applicable results and must be reviewed before relying on a gate."
)
CASE_DETAILS = (
    {
        "id": "blocked",
        "title": "1. Submitted close",
        "description": "USD 407M reported; detail reconstructs to USD 418M. Three blockers stop the close.",
        "changes": ["Original inconsistent forecast and budget, with explicit synthetic authorization limits."],
        "actions": [
            {"owner": "Cost lead", "action": "Reconcile CIV-100's USD 4M and MEP-200's USD 7M EAC shortfalls to AC + ETC."},
            {"owner": "Change controller", "action": "Reconcile MEP-200's USD 5M budget movement to approved change."},
            {"owner": "Scheduler", "action": "Review CIV-A100's zero remaining duration and -960 hours of float."},
        ],
        "gate_status": "blocked",
        "blockers": 3,
        "failures": 5,
    },
    {
        "id": "review",
        "title": "2. Forecast reconciled",
        "description": "The USD 11M arithmetic gap is resolved. Two schedule findings still require review.",
        "changes": [
            "CIV-100: EAC 126M to 130M; VAC -6M to -10M; submitted risk-adjusted EAC 146M to 150M.",
            "MEP-200: EAC 188M to 195M; VAC -8M to -15M; submitted risk-adjusted EAC 218M to 225M.",
            "MEP-200: current budget 185M to 180M, matching the supplied baseline plus approved changes.",
            "Schedule inputs are unchanged; financial reconciliation alone does not clear the schedule review.",
        ],
        "actions": [
            {"owner": "Scheduler", "action": "Review CIV-A100's status, remaining work and driving schedule logic; arithmetic checks cannot establish a feasible schedule."},
        ],
        "gate_status": "review",
        "blockers": 0,
        "failures": 2,
    },
    {
        "id": "ready",
        "title": "3. Selected controls satisfied",
        "description": "All 32 applicable checks pass. USD 65M of declared change and risk remains visible.",
        "changes": [
            "Financial inputs are identical to the reconciled case.",
            "CIV-A100: remaining duration 0 to 120 hours; total float -960 to +40 hours in a constructed replacement export.",
            "These supplied schedule values demonstrate the controls; EQ-Proof did not calculate or validate the revised schedule.",
        ],
        "actions": [
            {"owner": "Close owner", "action": "Review applicability, source completeness, the USD 65M declared exposure and the remaining schedule/commercial limitations before any approval."},
        ],
        "gate_status": "ready",
        "blockers": 0,
        "failures": 0,
    },
)


def json_bytes(payload: object, *, compact: bool = False) -> bytes:
    options = {"separators": (",", ":")} if compact else {"indent": 2}
    return (json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False, **options) + "\n").encode("utf-8")


def expected_result(details: dict) -> dict:
    blocked = details["id"] == "blocked"
    return {
        "gate_status": details["gate_status"],
        "blockers": details["blockers"],
        "failures": details["failures"],
        "equations_executed": 32,
        "not_applicable": 1,
        "portfolio": {
            "reported_eac": 407_000_000 if blocked else 418_000_000,
            "defensible_eac": 418_000_000,
            "deterministic_forecast_gap": 11_000_000 if blocked else 0,
            "configured_change_and_risk": 65_000_000,
            "submitted_risk_adjusted_eac": 472_000_000 if blocked else 483_000_000,
            "reconstructed_risk_adjusted_eac": 483_000_000,
            "risk_adjusted_reconciliation_gap": 11_000_000 if blocked else 0,
            "exposure_above_reported_eac": 76_000_000 if blocked else 65_000_000,
        },
    }


def assert_expected(room: dict, expected: dict) -> None:
    observed = {
        "gate_status": room["gate"]["status"],
        "blockers": room["gate"]["blockers"],
        "failures": room["gate"]["failures"],
        "equations_executed": room["analysis"]["equations_executed"],
        "not_applicable": room["analysis"]["summary"]["not_applicable"],
        "portfolio": {key: room["portfolio"][key] for key in expected["portfolio"]},
    }
    if observed != expected:
        raise ValueError(f"Showcase result changed: expected {expected!r}, observed {observed!r}")


def case_report(base: str, case: dict) -> str:
    room = case["control_room"]
    portfolio = room["portfolio"]
    metrics = (
        ("Reported EAC", "reported_eac"),
        ("Detail-reconstructed EAC (AC + ETC)", "defensible_eac"),
        ("Deterministic forecast gap", "deterministic_forecast_gap"),
        ("Declared change and configured risk", "configured_change_and_risk"),
        ("Reconstructed risk-adjusted position", "reconstructed_risk_adjusted_eac"),
        ("Submitted risk-adjusted summary", "submitted_risk_adjusted_eac"),
        ("Risk-adjusted reconciliation gap", "risk_adjusted_reconciliation_gap"),
        ("Position above reported EAC", "exposure_above_reported_eac"),
    )
    lines = [
        f"# {case['title']} — synthetic evidence", "", case["description"], "",
        "## Reconstructed position", "", "All values are synthetic USD; no currency conversion is performed.", "",
        "| Measure | USD |", "| --- | ---: |",
        *(f"| {label} | {portfolio[key]:,.0f} |" for label, key in metrics),
        "", "## Suggested review actions", "", "| Suggested owner | Action |", "| --- | --- |",
        *(f"| {item['owner']} | {item['action']} |" for item in case["actions"]),
        "", "Owners above are illustrative roles; no task has been assigned to a real person.",
        "", "## Input changes in this stage", "", *(f"- {change}" for change in case["changes"]),
        "", "## Applicability and limits", "", case["applicability_note"], "", case["boundary"],
        "", "## Source bytes", "", "| Source | SHA-256 |", "| --- | --- |",
        *(f"| [{source['name']}](../../../examples/close_walkthrough/{case['id']}/{source['name']}) | `{source['sha256']}` |" for source in case["source_files"]),
        "", "The JSON exports include the complete executed equation manifest and every pass, failure and not-applicable result.",
        "", "## Engine report", "", "",
    ]
    # Keep the engine report's sections nested under the scenario's evidence section.
    engine_sections = base.split("\n", 1)[1].strip()
    lines[-1] = "\n".join("#" + line if line.startswith("## ") else line for line in engine_sections.splitlines())
    lines.append("")
    return "\n".join(lines)


def build_artifacts() -> dict[Path, bytes]:
    artifacts: dict[Path, bytes] = {}
    cases = []
    for details in CASE_DETAILS:
        directory = FIXTURES / details["id"]
        sources = []
        for name, kind in SOURCE_KINDS:
            path = directory / name
            raw = path.read_bytes()
            if b"\r" in raw:
                raise ValueError(f"Showcase source must use LF: {path}")
            sources.append({
                "name": name, "kind": kind, "content": raw.decode("utf-8"),
                "sha256": hashlib.sha256(raw).hexdigest(),
            })
        records = [*parse_xer(directory / "schedule.xer"), *load_csv(directory / "cost.csv")]
        equations = [*CATALOGUE, *load_equations(directory / "custom_equations.json")]
        analysis = analyze(records, equations=equations, sources=[source["name"] for source in sources])
        room = build_control_room(records, analysis, currency="USD")
        room["demo"] = {
            "name": details["title"],
            "description": details["description"],
            "synthetic": True,
            "showcase_case": details["id"],
        }
        expected = expected_result(details)
        assert_expected(room, expected)
        case = {
            key: details[key] for key in ("id", "title", "description", "changes", "actions")
        }
        case.update({
            "synthetic": True, "currency": "USD", "boundary": BOUNDARY, "applicability_note": APPLICABILITY,
            "expected": expected, "source_files": sources, "control_room": room,
        })
        cases.append(case)
        target = EVIDENCE_OUTPUT / details["id"]
        with tempfile.TemporaryDirectory() as temporary:
            write_outputs(analysis, temporary)
            for name in ("analysis.json", "report.md", "exceptions.csv"):
                # The public CLI writers may follow OS line endings; evidence is canonical LF.
                content = Path(temporary, name).read_text(encoding="utf-8")
                if name == "report.md":
                    content = case_report(content, case)
                artifacts[target / name] = content.encode("utf-8")
        artifacts[target / "control-room.json"] = json_bytes(room)
    artifacts[WEB_OUTPUT] = json_bytes({"schema_version": "eq-proof/showcase-cases@1", "cases": cases}, compact=True)
    return artifacts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on missing or stale artifacts; write nothing.")
    arguments = parser.parse_args(argv)
    artifacts = build_artifacts()
    drift = []
    for relative, expected in artifacts.items():
        output = ROOT / relative
        if arguments.check:
            if not output.is_file() or output.read_bytes() != expected:
                drift.append(str(relative))
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(expected)
    if drift:
        print("Showcase evidence drift:\n" + "\n".join(drift))
        return 1
    print(f"{'Verified' if arguments.check else 'Generated'} {len(artifacts)} deterministic showcase artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
