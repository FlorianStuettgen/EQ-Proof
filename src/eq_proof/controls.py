"""Project-controls equation workbench and native export adapters."""

from __future__ import annotations

import ast
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class ControlsError(ValueError):
    """Raised when controls data or an equation pack is invalid."""


@dataclass(frozen=True)
class Equation:
    id: str
    title: str
    domain: str
    expression: str
    severity: str
    description: str
    remediation: str
    required_fields: tuple[str, ...]
    tolerance: float = 1e-6
    record_type: str = "control_account"


@dataclass(frozen=True)
class Finding:
    equation_id: str
    title: str
    domain: str
    severity: str
    record_type: str
    record_id: str
    status: str
    residual: float
    expression: str
    description: str
    remediation: str
    values: dict[str, float]


@dataclass(frozen=True)
class Analysis:
    sources: tuple[str, ...]
    records_analyzed: int
    equations_considered: int
    equations_executed: int
    findings: tuple[Finding, ...]

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.findings if item.status == "fail")

    @property
    def blockers(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.failures if item.severity == "blocker")

    @property
    def close_ready(self) -> bool:
        return not self.blockers

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": list(self.sources),
            "records_analyzed": self.records_analyzed,
            "equations_considered": self.equations_considered,
            "equations_executed": self.equations_executed,
            "close_ready": self.close_ready,
            "summary": {
                "blockers": len(self.blockers),
                "failures": len(self.failures),
                "passes": sum(1 for item in self.findings if item.status == "pass"),
                "not_applicable": sum(1 for item in self.findings if item.status == "not_applicable"),
            },
            "findings": [asdict(item) for item in self.findings],
        }


ALIASES: dict[str, tuple[str, ...]] = {
    "record_id": ("record_id", "control_account_id", "ca_id", "wbs_code", "task_code", "activity_id"),
    "BAC": ("BAC", "bac", "budget_at_completion", "current_budget"),
    "AC": ("AC", "ac", "actual_cost", "actuals"),
    "ETC": ("ETC", "etc", "estimate_to_complete", "remaining_cost"),
    "EAC": ("EAC", "eac", "estimate_at_completion", "forecast_at_completion"),
    "PV": ("PV", "pv", "planned_value", "bcws"),
    "EV": ("EV", "ev", "earned_value", "bcwp"),
    "CV": ("CV", "cv", "cost_variance"),
    "SV": ("SV", "sv", "schedule_variance"),
    "VAC": ("VAC", "vac", "variance_at_completion"),
    "CPI": ("CPI", "cpi", "cost_performance_index"),
    "SPI": ("SPI", "spi", "schedule_performance_index"),
    "baseline_budget": ("baseline_budget", "original_budget"),
    "approved_changes": ("approved_changes", "approved_change"),
    "current_budget": ("current_budget", "revised_budget"),
    "pending_change_exposure": ("pending_change_exposure", "pending_changes", "unapproved_changes"),
    "risk_exposure": ("risk_exposure", "quantified_risk", "emv"),
    "P80_EAC": ("P80_EAC", "p80_eac", "risk_adjusted_eac"),
    "actual_start": ("actual_start", "act_start_date"),
    "actual_finish": ("actual_finish", "act_end_date"),
    "early_start": ("early_start", "early_start_date"),
    "early_finish": ("early_finish", "early_end_date"),
    "late_finish": ("late_finish", "late_end_date"),
    "original_duration_hours": ("original_duration_hours", "target_drtn_hr_cnt"),
    "remaining_duration_hours": ("remaining_duration_hours", "remain_drtn_hr_cnt"),
    "total_float_hours": ("total_float_hours", "total_float_hr_cnt"),
    "physical_percent_complete": ("physical_percent_complete", "phys_complete_pct"),
    "status_code": ("status_code", "task_status"),
}


CATALOGUE: tuple[Equation, ...] = (
    Equation("cost.eac_identity", "EAC equals actual cost plus ETC", "cost", "EAC == AC + ETC", "blocker", "The forecast at completion must reconcile to actual cost plus remaining forecast.", "Reconcile the cost ledger and forecast detail; do not post the close until the identity holds.", ("EAC", "AC", "ETC")),
    Equation("cost.vac_identity", "VAC equals BAC minus EAC", "cost", "VAC == BAC - EAC", "major", "Variance at completion must agree with the approved budget and current EAC.", "Recalculate VAC from governed BAC and EAC.", ("VAC", "BAC", "EAC")),
    Equation("evm.cv_identity", "Cost variance equals EV minus AC", "earned_value", "CV == EV - AC", "major", "Reported cost variance must reconcile to earned value and actual cost.", "Recalculate CV and investigate source-period or currency mismatches.", ("CV", "EV", "AC")),
    Equation("evm.sv_identity", "Schedule variance equals EV minus PV", "earned_value", "SV == EV - PV", "major", "Reported schedule variance must reconcile to earned and planned value.", "Recalculate SV and verify the status date and baseline time-phasing.", ("SV", "EV", "PV")),
    Equation("evm.cpi_identity", "CPI equals EV divided by AC", "earned_value", "CPI == EV / AC", "major", "The cost performance index must be derived from the same EV and AC basis.", "Recalculate CPI; verify zero-value, currency and accounting-period handling.", ("CPI", "EV", "AC"), tolerance=1e-4),
    Equation("evm.spi_identity", "SPI equals EV divided by PV", "earned_value", "SPI == EV / PV", "major", "The schedule performance index must be derived from the same EV and PV basis.", "Recalculate SPI and verify baseline and status-period alignment.", ("SPI", "EV", "PV"), tolerance=1e-4),
    Equation("change.budget_bridge", "Current budget bridges baseline and approved change", "change", "current_budget == baseline_budget + approved_changes", "blocker", "Current budget must be traceable to the baseline plus approved change.", "Locate unauthorized budget movement or missing approved change records.", ("current_budget", "baseline_budget", "approved_changes")),
    Equation("risk.p80_bridge", "P80 EAC includes pending change and risk exposure", "risk", "P80_EAC == EAC + pending_change_exposure + risk_exposure", "major", "Risk-adjusted EAC should bridge the deterministic forecast, pending change and quantified risk.", "Reconcile the risk register and pending-change log to the forecast.", ("P80_EAC", "EAC", "pending_change_exposure", "risk_exposure")),
    Equation("schedule.progress_duration", "In-progress activity retains remaining duration", "schedule", "remaining_duration_hours > 0", "major", "An in-progress activity should retain positive remaining duration.", "Correct activity status, actual finish or remaining duration in P6.", ("remaining_duration_hours", "status_code"), record_type="activity"),
    Equation("schedule.float_reasonable", "Total float is within an operational review range", "schedule", "total_float_hours >= -800", "minor", "Extreme negative float often indicates broken constraints, calendars or missed contractual dates.", "Review constraints, calendars and driving relationships before accepting the schedule.", ("total_float_hours",), record_type="activity"),
)


_ALLOWED_FUNCTIONS = {"abs": abs, "min": min, "max": max, "round": round}


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ControlsError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ControlsError(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ControlsError(f"{label} must be finite")
    return number


def _eval(node: ast.AST, values: Mapping[str, float]) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return _number(node.value, "constant")
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise KeyError(node.id)
        return values[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _eval(node.operand, values)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left, right = _eval(node.left, values), _eval(node.right, values)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise ZeroDivisionError
        return left / right
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUNCTIONS:
        if node.keywords:
            raise ControlsError("Keyword arguments are not supported")
        return float(_ALLOWED_FUNCTIONS[node.func.id](*[_eval(arg, values) for arg in node.args]))
    raise ControlsError("Unsupported equation syntax")


def evaluate(expression: str, values: Mapping[str, float], tolerance: float) -> tuple[bool, float]:
    if len(expression) > 4096:
        raise ControlsError("Equation exceeds the 4096-character limit")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ControlsError(f"Invalid equation: {expression}") from exc
    if sum(1 for _ in ast.walk(tree)) > 2048:
        raise ControlsError("Equation is too complex")
    body = tree.body
    if not isinstance(body, ast.Compare) or len(body.ops) != 1 or len(body.comparators) != 1:
        raise ControlsError("Equation must contain exactly one comparison")
    left = _eval(body.left, values)
    right = _eval(body.comparators[0], values)
    residual = left - right
    op = body.ops[0]
    if isinstance(op, ast.Eq):
        return abs(residual) <= tolerance, residual
    if isinstance(op, ast.LtE):
        return residual <= tolerance, max(0.0, residual)
    if isinstance(op, ast.GtE):
        return residual >= -tolerance, max(0.0, -residual)
    if isinstance(op, ast.Lt):
        return residual < 0, max(0.0, residual)
    if isinstance(op, ast.Gt):
        return residual > 0, max(0.0, -residual)
    raise ControlsError("Only ==, <=, >=, < and > are supported")


def normalize_row(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = dict(row)
    casefolded = {str(key).casefold(): value for key, value in row.items()}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in row:
                normalized[canonical] = row[alias]
                break
            if alias.casefold() in casefolded:
                normalized[canonical] = casefolded[alias.casefold()]
                break
    return normalized


def load_csv(path: str | Path, record_type: str = "control_account") -> list[dict[str, Any]]:
    source = Path(path)
    with source.open(newline="", encoding="utf-8-sig") as handle:
        rows = []
        for index, row in enumerate(csv.DictReader(handle), start=2):
            normalized = normalize_row(row)
            normalized["_record_type"] = record_type
            normalized["_source"] = str(source)
            normalized["_row"] = index
            rows.append(normalized)
    return rows


def parse_xer(path: str | Path) -> list[dict[str, Any]]:
    """Parse Primavera P6 XER tables and return canonical activity rows."""
    source = Path(path)
    tables: dict[str, list[dict[str, str]]] = {}
    table = ""
    fields: list[str] = []
    with source.open(encoding="utf-8-sig", errors="replace") as handle:
        for raw in handle:
            parts = raw.rstrip("\r\n").split("\t")
            marker = parts[0] if parts else ""
            if marker == "%T":
                table = parts[1]
                fields = []
                tables.setdefault(table, [])
            elif marker == "%F":
                fields = parts[1:]
            elif marker == "%R" and table and fields:
                values = parts[1:] + [""] * max(0, len(fields) - len(parts[1:]))
                tables[table].append(dict(zip(fields, values)))
    activities = []
    for row in tables.get("TASK", []):
        normalized = normalize_row(row)
        normalized["record_id"] = row.get("task_code") or row.get("task_id") or "unknown"
        normalized["activity_name"] = row.get("task_name", "")
        normalized["wbs_id"] = row.get("wbs_id", "")
        normalized["_record_type"] = "activity"
        normalized["_source"] = str(source)
        activities.append(normalized)
    if not activities:
        raise ControlsError("No TASK records were found in the P6 XER")
    return activities


def load_equations(path: str | Path) -> tuple[Equation, ...]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, list):
        raise ControlsError("Equation pack must be a JSON array")
    equations = []
    for item in document:
        if not isinstance(item, dict):
            raise ControlsError("Each equation must be an object")
        required = item.get("required_fields", [])
        if not isinstance(required, list) or not all(isinstance(value, str) for value in required):
            raise ControlsError("required_fields must be a string array")
        equations.append(Equation(id=str(item["id"]), title=str(item.get("title", item["id"])), domain=str(item.get("domain", "custom")), expression=str(item["expression"]), severity=str(item.get("severity", "major")), description=str(item.get("description", "")), remediation=str(item.get("remediation", "Review the source data and equation.")), required_fields=tuple(required), tolerance=_number(item.get("tolerance", 1e-6), "tolerance"), record_type=str(item.get("record_type", "control_account"))))
    return tuple(equations)


def _coerce_values(row: Mapping[str, Any], fields: Sequence[str]) -> dict[str, float] | None:
    output: dict[str, float] = {}
    for field in fields:
        if field == "status_code":
            continue
        value = row.get(field)
        if value in (None, ""):
            return None
        try:
            output[field] = _number(value, field)
        except ControlsError:
            return None
    return output


def analyze(records: Sequence[Mapping[str, Any]], *, equations: Sequence[Equation] = CATALOGUE, sources: Iterable[str] = ()) -> Analysis:
    findings: list[Finding] = []
    executed = 0
    severity_order = {"blocker": 0, "major": 1, "minor": 2, "info": 3}
    for raw in records:
        row = normalize_row(raw)
        record_type = str(row.get("_record_type", "control_account"))
        record_id = str(row.get("record_id") or row.get("task_code") or row.get("_row") or "unknown")
        for equation in equations:
            if equation.record_type != record_type:
                continue
            values = _coerce_values(row, equation.required_fields)
            if values is None:
                findings.append(Finding(equation.id, equation.title, equation.domain, equation.severity, record_type, record_id, "not_applicable", 0.0, equation.expression, equation.description, equation.remediation, {}))
                continue
            if equation.id == "schedule.progress_duration":
                status = str(row.get("status_code", "")).casefold()
                if not any(token in status for token in ("progress", "active", "tk_active")):
                    findings.append(Finding(equation.id, equation.title, equation.domain, equation.severity, record_type, record_id, "not_applicable", 0.0, equation.expression, equation.description, equation.remediation, values))
                    continue
            executed += 1
            try:
                passed, residual = evaluate(equation.expression, values, equation.tolerance)
                status = "pass" if passed else "fail"
            except ZeroDivisionError:
                status, residual = "fail", math.inf
            findings.append(Finding(equation.id, equation.title, equation.domain, equation.severity, record_type, record_id, status, residual, equation.expression, equation.description, equation.remediation, values))
    findings.sort(key=lambda item: (0 if item.status == "fail" else 1 if item.status == "pass" else 2, severity_order.get(item.severity, 9), -abs(item.residual) if math.isfinite(item.residual) else float("-inf"), item.record_id, item.equation_id))
    return Analysis(sources=tuple(sources), records_analyzed=len(records), equations_considered=len(equations), equations_executed=executed, findings=tuple(findings))


def render_markdown(analysis: Analysis) -> str:
    rows = []
    for finding in analysis.failures:
        residual = "∞" if not math.isfinite(finding.residual) else f"{finding.residual:.6g}"
        rows.append(f"| `{finding.severity}` | `{finding.record_id}` | `{finding.equation_id}` | `{residual}` | {finding.remediation} |")
    exceptions = "\n".join(rows) or "| — | — | — | — | No exceptions |"
    return f"""# EQ-Proof Project Controls Assurance Report

## Close gate

| Metric | Value |
| --- | ---: |
| Close ready | **{'YES' if analysis.close_ready else 'NO'}** |
| Records analyzed | {analysis.records_analyzed} |
| Equations executed | {analysis.equations_executed} |
| Blockers | {len(analysis.blockers)} |
| Total failures | {len(analysis.failures)} |

## Ranked exception register

| Severity | Record | Equation | Residual | Required action |
| --- | --- | --- | ---: | --- |
{exceptions}

## Operating boundary

The workbench evaluates the supplied exports and equations. It does not replace source-system governance, approve changes, or infer contractual truth. Catalogue and user equations are stored with the output so the result can be reproduced.
"""


def write_outputs(analysis: Analysis, directory: str | Path) -> None:
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(json.dumps(analysis.to_dict(), indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    (output / "report.md").write_text(render_markdown(analysis), encoding="utf-8")
    with (output / "exceptions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["severity", "record_type", "record_id", "equation_id", "residual", "remediation"])
        for item in analysis.failures:
            writer.writerow([item.severity, item.record_type, item.record_id, item.equation_id, item.residual, item.remediation])
