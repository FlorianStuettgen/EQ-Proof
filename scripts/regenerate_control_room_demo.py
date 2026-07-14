"""Regenerate the deterministic Control Room demo payload."""

from __future__ import annotations

import json
from pathlib import Path

from eq_proof.control_room import build_control_room
from eq_proof.controls import CATALOGUE, analyze, load_csv, load_equations, parse_xer

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "hyperscale_close"
OUTPUT = ROOT / "src" / "eq_proof" / "web" / "demo-data.json"
CATALOGUE_FIELDS = (
    "id",
    "title",
    "domain",
    "expression",
    "severity",
    "record_type",
    "applicability_field",
    "applicability_values",
)


def main() -> int:
    records = [
        *parse_xer(FIXTURE / "schedule.xer"),
        *load_csv(FIXTURE / "cost.csv"),
    ]
    equations = [
        *CATALOGUE,
        *load_equations(FIXTURE / "custom_equations.json"),
    ]
    analysis = analyze(
        records,
        equations=equations,
        sources=(
            "schedule.xer",
            "cost.csv",
            "custom_equations.json",
        ),
    )
    compiled = build_control_room(records, analysis, currency="USD")
    payload = {
        key: compiled[key]
        for key in (
            "schema_version",
            "units",
            "gate",
            "assurance",
            "portfolio",
            "surprise",
            "domain_summary",
            "exceptions",
            "graph",
        )
    }
    payload["analysis"] = {
        key: compiled["analysis"][key]
        for key in (
            "sources",
            "source_manifest",
            "records_analyzed",
            "equations_considered",
            "equations_executed",
            "close_ready",
            "gate_status",
            "summary",
        )
    }
    payload["catalogue"] = [
        {
            key: equation.__dict__[key]
            for key in CATALOGUE_FIELDS
        }
        for equation in CATALOGUE
    ]
    payload["demo"] = {
        "name": "Hyperscale data-centre monthly close",
        "description": "Synthetic schedule, cost, change and risk data designed to expose deterministic and risk-adjusted reconciliation gaps.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Generated {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
