"""Executive reconstruction and evidence graph for project-controls analyses."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .controls import Analysis, Finding, normalize_row

CONTROL_ROOM_SCHEMA = "eq-proof/control-room@1"


def _finite(row: Mapping[str, Any], field: str) -> float | None:
    value = row.get(field)
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _impact_metric(finding: Finding) -> str:
    if finding.domain == "risk":
        return "risk_adjusted_eac"
    if finding.domain in {"cost", "earned_value", "change", "governance"}:
        return "defensible_eac"
    if finding.domain == "schedule":
        return "forecast_confidence"
    return "close_gate"


def _confidence_score(analysis: Analysis) -> int:
    penalty = 0
    for finding in analysis.failures:
        penalty += {"blocker": 18, "major": 7, "minor": 2, "info": 1}.get(
            finding.severity, 4
        )
    return max(0, min(100, 100 - penalty))


def _portfolio(records: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reported_eac = 0.0
    defensible_eac = 0.0
    submitted_p80 = 0.0
    defensible_p80 = 0.0
    accounts = 0
    contributions: list[dict[str, Any]] = []

    for raw in records:
        row = normalize_row(raw)
        if str(row.get("_record_type", "control_account")) != "control_account":
            continue
        reported = _finite(row, "EAC")
        actual = _finite(row, "AC")
        remaining = _finite(row, "ETC")
        pending = _finite(row, "pending_change_exposure") or 0.0
        risk = _finite(row, "risk_exposure") or 0.0
        submitted_risk = _finite(row, "P80_EAC")
        if reported is None and (actual is None or remaining is None):
            continue

        accounts += 1
        governed = actual + remaining if actual is not None and remaining is not None else reported
        assert governed is not None
        reported_value = reported if reported is not None else governed
        reconstructed_p80 = governed + pending + risk
        submitted_risk_value = submitted_risk if submitted_risk is not None else reported_value + pending + risk

        deterministic_gap = governed - reported_value
        hidden_exposure = reconstructed_p80 - reported_value
        record_id = str(row.get("record_id") or row.get("_row") or "unknown")
        contributions.append(
            {
                "record_id": record_id,
                "reported_eac": reported_value,
                "defensible_eac": governed,
                "deterministic_gap": deterministic_gap,
                "pending_change": pending,
                "risk_exposure": risk,
                "submitted_p80": submitted_risk_value,
                "defensible_p80": reconstructed_p80,
                "hidden_exposure": hidden_exposure,
                "source": Path(str(row.get("_source", "uploaded data"))).name,
            }
        )
        reported_eac += reported_value
        defensible_eac += governed
        submitted_p80 += submitted_risk_value
        defensible_p80 += reconstructed_p80

    contributions.sort(key=lambda item: (-abs(item["hidden_exposure"]), item["record_id"]))
    portfolio = {
        "accounts_reconstructed": accounts,
        "reported_eac": reported_eac,
        "defensible_eac": defensible_eac,
        "submitted_p80": submitted_p80,
        "defensible_p80": defensible_p80,
        "deterministic_gap": defensible_eac - reported_eac,
        "risk_adjustment_gap": defensible_p80 - submitted_p80,
        "hidden_exposure": defensible_p80 - reported_eac,
        "quantified_change_and_risk": defensible_p80 - defensible_eac,
    }
    return portfolio, contributions


def _graph(
    contributions: Sequence[Mapping[str, Any]], failures: Sequence[Finding]
) -> dict[str, list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = [
        {"id": "metric:reported", "kind": "metric", "label": "Reported EAC", "metric": "reported_eac"},
        {"id": "metric:defensible", "kind": "metric", "label": "Defensible EAC", "metric": "defensible_eac"},
        {"id": "metric:risk", "kind": "metric", "label": "Defensible P80", "metric": "risk_adjusted_eac"},
        {"id": "metric:hidden", "kind": "decision", "label": "Hidden exposure", "metric": "hidden_exposure"},
    ]
    edges: list[dict[str, Any]] = [
        {"source": "metric:reported", "target": "metric:hidden", "relation": "compared_with"},
        {"source": "metric:defensible", "target": "metric:risk", "relation": "risk_adjusted_to"},
        {"source": "metric:risk", "target": "metric:hidden", "relation": "exposes"},
    ]

    account_ids = {str(item["record_id"]) for item in contributions}
    for item in contributions:
        node_id = f"account:{item['record_id']}"
        nodes.append(
            {
                "id": node_id,
                "kind": "account",
                "label": str(item["record_id"]),
                "hidden_exposure": float(item["hidden_exposure"]),
            }
        )
        edges.extend(
            [
                {"source": node_id, "target": "metric:reported", "relation": "reports"},
                {"source": node_id, "target": "metric:defensible", "relation": "reconstructs"},
                {"source": node_id, "target": "metric:risk", "relation": "risk_adjusts"},
            ]
        )

    for index, finding in enumerate(failures):
        finding_id = f"finding:{index}:{finding.equation_id}:{finding.record_id}"
        nodes.append(
            {
                "id": finding_id,
                "kind": "finding",
                "label": finding.title,
                "severity": finding.severity,
                "record_id": finding.record_id,
                "equation_id": finding.equation_id,
                "residual": finding.residual,
            }
        )
        account_id = f"account:{finding.record_id}"
        if finding.record_id not in account_ids:
            nodes.append(
                {
                    "id": account_id,
                    "kind": finding.record_type,
                    "label": finding.record_id,
                }
            )
            account_ids.add(finding.record_id)
        edges.append({"source": account_id, "target": finding_id, "relation": "violates"})
        target = {
            "defensible_eac": "metric:defensible",
            "risk_adjusted_eac": "metric:risk",
            "forecast_confidence": "metric:hidden",
            "close_gate": "metric:hidden",
        }[_impact_metric(finding)]
        edges.append({"source": finding_id, "target": target, "relation": "impacts"})

    return {"nodes": nodes, "edges": edges}


def build_control_room(
    records: Sequence[Mapping[str, Any]], analysis: Analysis
) -> dict[str, Any]:
    """Compile equation results into an executive control-room payload."""
    portfolio, contributions = _portfolio(records)
    failures = list(analysis.failures)
    domain_counts = Counter(item.domain for item in failures)
    blocker_counts = Counter(item.domain for item in analysis.blockers)
    domains = [
        {
            "domain": domain,
            "failures": count,
            "blockers": blocker_counts.get(domain, 0),
        }
        for domain, count in sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    confidence = _confidence_score(analysis)
    gate_status = "ready" if analysis.close_ready else "blocked"
    hidden = portfolio["hidden_exposure"]
    headline = (
        "The submitted close is internally defensible."
        if analysis.close_ready and abs(hidden) <= 1e-6
        else f"The reported EAC excludes {hidden:,.0f} of reconstructed deterministic, change and risk exposure."
    )
    return {
        "schema_version": CONTROL_ROOM_SCHEMA,
        "gate": {
            "status": gate_status,
            "label": "CLOSE READY" if analysis.close_ready else "CLOSE BLOCKED",
            "confidence_score": confidence,
            "blockers": len(analysis.blockers),
            "failures": len(failures),
            "headline": headline,
        },
        "portfolio": portfolio,
        "surprise": {
            "headline": headline,
            "contributions": contributions,
        },
        "domain_summary": domains,
        "exceptions": [
            {
                **finding.__dict__,
                "impact_metric": _impact_metric(finding),
                "materiality": abs(finding.residual)
                if math.isfinite(finding.residual)
                else None,
            }
            for finding in failures
        ],
        "graph": _graph(contributions, failures),
        "analysis": analysis.to_dict(),
    }
