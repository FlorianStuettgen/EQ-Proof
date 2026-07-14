"""Executive reconstruction and evidence graph for project-controls analyses."""

from __future__ import annotations

import math
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .controls import Analysis, Finding, normalize_row

CONTROL_ROOM_SCHEMA = "eq-proof/control-room@2"
GRAPH_MAX_ACCOUNTS = 40
GRAPH_MAX_FINDINGS = 60


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
    if finding.domain == "cost":
        return "deterministic_forecast_gap"
    if finding.domain == "risk":
        return "risk_adjusted_reconciliation"
    if finding.domain == "change":
        return "baseline_governance"
    if finding.domain == "earned_value":
        return "earned_value_assurance"
    if finding.domain == "schedule":
        return "schedule_assurance"
    return "close_gate"


def _assurance(analysis: Analysis) -> dict[str, Any]:
    penalty = sum(
        {
            "blocker": 18,
            "major": 7,
            "minor": 2,
            "info": 1,
        }.get(finding.severity, 4)
        for finding in analysis.failures
    )
    score = max(0, min(100, 100 - penalty))
    label = (
        "high"
        if score >= 85
        else "moderate"
        if score >= 65
        else "low"
    )
    return {
        "score": score,
        "label": label,
        "method": "deterministic severity penalty heuristic v1",
        "calibrated_probability": False,
        "note": "This is a transparent triage indicator, not a statistical confidence interval.",
    }


def _portfolio(
    records: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    reported_eac = 0.0
    defensible_eac = 0.0
    reconstructed_risk_adjusted = 0.0
    submitted_risk_adjusted = 0.0
    submitted_count = 0
    configured_change_and_risk = 0.0
    accounts = 0
    contributions: list[dict[str, Any]] = []

    for raw in records:
        row = normalize_row(raw)
        if (
            str(row.get("_record_type", "control_account"))
            != "control_account"
        ):
            continue
        reported = _finite(row, "EAC")
        actual = _finite(row, "AC")
        remaining = _finite(row, "ETC")
        pending = _finite(row, "pending_change_exposure") or 0.0
        risk = _finite(row, "risk_exposure") or 0.0
        submitted_adjusted = _finite(row, "risk_adjusted_EAC")
        if reported is None and (actual is None or remaining is None):
            continue

        accounts += 1
        governed = (
            actual + remaining
            if actual is not None and remaining is not None
            else reported
        )
        assert governed is not None
        reported_value = reported if reported is not None else governed
        reconstructed_adjusted = governed + pending + risk
        deterministic_gap = governed - reported_value
        exposure_above_reported = reconstructed_adjusted - reported_value
        reconciliation_gap = (
            reconstructed_adjusted - submitted_adjusted
            if submitted_adjusted is not None
            else None
        )
        if submitted_adjusted is not None:
            submitted_count += 1
            submitted_risk_adjusted += submitted_adjusted

        record_id = str(
            row.get("record_id") or row.get("_row") or "unknown"
        )
        contributions.append(
            {
                "record_id": record_id,
                "reported_eac": reported_value,
                "defensible_eac": governed,
                "deterministic_forecast_gap": deterministic_gap,
                "pending_change": pending,
                "configured_risk_uplift": risk,
                "submitted_risk_adjusted_eac": submitted_adjusted,
                "reconstructed_risk_adjusted_eac": reconstructed_adjusted,
                "risk_adjusted_reconciliation_gap": reconciliation_gap,
                "exposure_above_reported_eac": exposure_above_reported,
                "source": Path(
                    str(row.get("_source", "uploaded data"))
                ).name,
            }
        )
        reported_eac += reported_value
        defensible_eac += governed
        configured_change_and_risk += pending + risk
        reconstructed_risk_adjusted += reconstructed_adjusted

    contributions.sort(
        key=lambda item: (
            -abs(item["deterministic_forecast_gap"]),
            -abs(item["exposure_above_reported_eac"]),
            item["record_id"],
        )
    )
    complete_risk_summary = accounts > 0 and submitted_count == accounts
    submitted_total: float | None = (
        submitted_risk_adjusted if complete_risk_summary else None
    )
    portfolio = {
        "accounts_reconstructed": accounts,
        "reported_eac": reported_eac,
        "defensible_eac": defensible_eac,
        "deterministic_forecast_gap": defensible_eac - reported_eac,
        "configured_change_and_risk": configured_change_and_risk,
        "submitted_risk_adjusted_eac": submitted_total,
        "reconstructed_risk_adjusted_eac": reconstructed_risk_adjusted,
        "risk_adjusted_reconciliation_gap": (
            reconstructed_risk_adjusted - submitted_risk_adjusted
            if complete_risk_summary
            else None
        ),
        "risk_adjusted_summary_coverage": {
            "submitted_accounts": submitted_count,
            "reconstructed_accounts": accounts,
            "complete": complete_risk_summary,
        },
        "exposure_above_reported_eac": (
            reconstructed_risk_adjusted - reported_eac
        ),
    }
    return portfolio, contributions


def _impact_nodes() -> list[dict[str, Any]]:
    return [
        {
            "id": "metric:reported",
            "kind": "metric",
            "label": "Reported EAC",
            "metric": "reported_eac",
        },
        {
            "id": "metric:defensible",
            "kind": "metric",
            "label": "Defensible EAC",
            "metric": "defensible_eac",
        },
        {
            "id": "metric:deterministic_gap",
            "kind": "metric",
            "label": "Deterministic forecast gap",
            "metric": "deterministic_forecast_gap",
        },
        {
            "id": "metric:risk_adjusted",
            "kind": "metric",
            "label": "Risk-adjusted position",
            "metric": "reconstructed_risk_adjusted_eac",
        },
        {
            "id": "metric:risk_reconciliation",
            "kind": "metric",
            "label": "Risk-adjusted reconciliation",
            "metric": "risk_adjusted_reconciliation_gap",
        },
        {
            "id": "assurance:baseline",
            "kind": "assurance",
            "label": "Baseline governance",
            "metric": "baseline_governance",
        },
        {
            "id": "assurance:earned_value",
            "kind": "assurance",
            "label": "Earned-value assurance",
            "metric": "earned_value_assurance",
        },
        {
            "id": "assurance:schedule",
            "kind": "assurance",
            "label": "Schedule assurance",
            "metric": "schedule_assurance",
        },
        {
            "id": "decision:gate",
            "kind": "decision",
            "label": "Close gate",
            "metric": "close_gate",
        },
    ]


def _graph(
    contributions: Sequence[Mapping[str, Any]],
    failures: Sequence[Finding],
) -> dict[str, Any]:
    shown_contributions = list(contributions[:GRAPH_MAX_ACCOUNTS])
    shown_failures = list(failures[:GRAPH_MAX_FINDINGS])
    nodes = _impact_nodes()
    edges: list[dict[str, Any]] = [
        {
            "source": "metric:reported",
            "target": "metric:deterministic_gap",
            "relation": "compared_with",
        },
        {
            "source": "metric:defensible",
            "target": "metric:deterministic_gap",
            "relation": "compared_with",
        },
        {
            "source": "metric:defensible",
            "target": "metric:risk_adjusted",
            "relation": "adjusted_by_declared_exposure",
        },
        {
            "source": "metric:risk_adjusted",
            "target": "decision:gate",
            "relation": "informs",
        },
    ]

    account_ids = {
        str(item["record_id"]) for item in shown_contributions
    }
    for item in shown_contributions:
        node_id = f"account:{item['record_id']}"
        nodes.append(
            {
                "id": node_id,
                "kind": "account",
                "label": str(item["record_id"]),
                "deterministic_forecast_gap": float(
                    item["deterministic_forecast_gap"]
                ),
                "exposure_above_reported_eac": float(
                    item["exposure_above_reported_eac"]
                ),
            }
        )
        edges.extend(
            [
                {
                    "source": node_id,
                    "target": "metric:reported",
                    "relation": "reports",
                },
                {
                    "source": node_id,
                    "target": "metric:defensible",
                    "relation": "reconstructs",
                },
                {
                    "source": node_id,
                    "target": "metric:risk_adjusted",
                    "relation": "risk_adjusts",
                },
            ]
        )

    target_map = {
        "deterministic_forecast_gap": "metric:deterministic_gap",
        "risk_adjusted_reconciliation": "metric:risk_reconciliation",
        "baseline_governance": "assurance:baseline",
        "earned_value_assurance": "assurance:earned_value",
        "schedule_assurance": "assurance:schedule",
        "close_gate": "decision:gate",
    }
    for index, finding in enumerate(shown_failures):
        finding_id = (
            f"finding:{index}:{finding.equation_id}:{finding.record_id}"
        )
        nodes.append(
            {
                "id": finding_id,
                "kind": "finding",
                "label": finding.title,
                "severity": finding.severity,
                "record_id": finding.record_id,
                "equation_id": finding.equation_id,
                "residual": finding.residual
                if math.isfinite(finding.residual)
                else None,
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
        edges.append(
            {
                "source": account_id,
                "target": finding_id,
                "relation": "violates",
            }
        )
        impact = _impact_metric(finding)
        edges.append(
            {
                "source": finding_id,
                "target": target_map[impact],
                "relation": "affects",
            }
        )
        edges.append(
            {
                "source": finding_id,
                "target": "decision:gate",
                "relation": "gates",
            }
        )

    return {
        "nodes": nodes,
        "edges": edges,
        "limits": {
            "accounts_shown": len(shown_contributions),
            "accounts_total": len(contributions),
            "findings_shown": len(shown_failures),
            "findings_total": len(failures),
            "truncated": (
                len(shown_contributions) < len(contributions)
                or len(shown_failures) < len(failures)
            ),
        },
    }


def _headline(portfolio: Mapping[str, Any], status: str) -> str:
    deterministic = float(portfolio["deterministic_forecast_gap"])
    exposure = float(portfolio["exposure_above_reported_eac"])
    reconciliation = portfolio["risk_adjusted_reconciliation_gap"]
    if (
        status == "ready"
        and abs(deterministic) <= 1e-6
        and (
            reconciliation is None
            or abs(float(reconciliation)) <= 1e-6
        )
    ):
        return "The submitted close reconciles to the declared deterministic and risk-adjusted controls."
    parts = []
    if abs(deterministic) > 1e-6:
        direction = "below" if deterministic > 0 else "above"
        parts.append(
            f"Reported EAC is {abs(deterministic):,.0f} {direction} governed AC + ETC"
        )
    if abs(exposure) > 1e-6:
        direction = "above" if exposure > 0 else "below"
        parts.append(
            f"the configured risk-adjusted position is {abs(exposure):,.0f} {direction} reported EAC"
        )
    if reconciliation is not None and abs(float(reconciliation)) > 1e-6:
        direction = "below" if float(reconciliation) > 0 else "above"
        parts.append(
            f"the submitted risk-adjusted summary is {abs(float(reconciliation)):,.0f} {direction} the reconstructed bridge"
        )
    text = "; ".join(parts)
    return (
        text[:1].upper() + text[1:]
        if text
        else "Close requires review"
    ) + "."


def build_control_room(
    records: Sequence[Mapping[str, Any]],
    analysis: Analysis,
    *,
    currency: str = "USD",
) -> dict[str, Any]:
    """Compile equation results into an executive control-room payload."""
    if (
        not isinstance(currency, str)
        or len(currency) != 3
        or not currency.isalpha()
    ):
        raise ValueError("currency must be a three-letter code")
    currency = currency.upper()
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
        for domain, count in sorted(
            domain_counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    assurance = _assurance(analysis)
    gate_status = analysis.gate_status
    gate_label = {
        "blocked": "CLOSE BLOCKED",
        "review": "REVIEW REQUIRED",
        "ready": "CLOSE READY",
    }[gate_status]
    headline = _headline(portfolio, gate_status)
    return {
        "schema_version": CONTROL_ROOM_SCHEMA,
        "units": {"currency": currency, "duration": "hours"},
        "gate": {
            "status": gate_status,
            "label": gate_label,
            "blockers": len(analysis.blockers),
            "failures": len(failures),
            "headline": headline,
        },
        "assurance": assurance,
        "portfolio": portfolio,
        "surprise": {
            "headline": headline,
            "contributions": contributions,
        },
        "domain_summary": domains,
        "exceptions": [
            {
                **finding.to_dict(),
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
