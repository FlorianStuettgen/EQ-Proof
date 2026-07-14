"""Project-controls equation workbench and native export adapters."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import keyword
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


class ControlsError(ValueError):
    """Raised when controls data or an equation pack is invalid."""


SEVERITIES = ("blocker", "major", "minor", "info")
RECORD_TYPES = ("control_account", "activity")
SEVERITY_RANK = {name: index for index, name in enumerate(SEVERITIES)}
MAX_EQUATIONS = 500
MAX_EXPRESSION_LENGTH = 4096
MAX_EXPRESSION_NODES = 2048
MAX_CSV_ROWS = 500_000
MAX_XER_ROWS = 1_000_000
_EQUATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_ALLOWED_FUNCTIONS = {"abs": abs, "min": min, "max": max, "round": round}
_ALLOWED_DOCUMENT_FIELDS = {
    "id",
    "title",
    "domain",
    "expression",
    "severity",
    "description",
    "remediation",
    "required_fields",
    "tolerance",
    "record_type",
    "applies_when",
}


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
    applicability_field: str | None = None
    applicability_values: tuple[str, ...] = ()


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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if not math.isfinite(self.residual):
            payload["residual"] = None
            payload["residual_state"] = "non_finite"
        else:
            payload["residual_state"] = "finite"
        return payload


@dataclass(frozen=True)
class Analysis:
    sources: tuple[str, ...]
    records_analyzed: int
    equations_considered: int
    equations_executed: int
    findings: tuple[Finding, ...]
    equations: tuple[Equation, ...] = ()
    source_manifest: tuple[dict[str, Any], ...] = ()

    @property
    def failures(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.findings if item.status == "fail")

    @property
    def blockers(self) -> tuple[Finding, ...]:
        return tuple(item for item in self.failures if item.severity == "blocker")

    @property
    def close_ready(self) -> bool:
        return not self.blockers

    @property
    def gate_status(self) -> str:
        if self.blockers:
            return "blocked"
        if self.failures:
            return "review"
        return "ready"

    def fails_at_or_above(self, severity: str) -> bool:
        if severity == "never":
            return False
        if severity not in SEVERITY_RANK:
            raise ControlsError(f"Unknown failure threshold: {severity}")
        threshold = SEVERITY_RANK[severity]
        return any(
            SEVERITY_RANK.get(item.severity, 99) <= threshold
            for item in self.failures
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sources": list(self.sources),
            "source_manifest": list(self.source_manifest),
            "records_analyzed": self.records_analyzed,
            "equations_considered": self.equations_considered,
            "equations_executed": self.equations_executed,
            "close_ready": self.close_ready,
            "gate_status": self.gate_status,
            "summary": {
                "blockers": len(self.blockers),
                "failures": len(self.failures),
                "passes": sum(
                    1 for item in self.findings if item.status == "pass"
                ),
                "not_applicable": sum(
                    1
                    for item in self.findings
                    if item.status == "not_applicable"
                ),
            },
            "equations": [asdict(item) for item in self.equations],
            "findings": [item.to_dict() for item in self.findings],
        }


ALIASES: dict[str, tuple[str, ...]] = {
    "record_id": (
        "record_id",
        "control_account_id",
        "ca_id",
        "wbs_code",
        "task_code",
        "activity_id",
    ),
    "BAC": ("BAC", "bac", "budget_at_completion"),
    "AC": ("AC", "ac", "actual_cost", "actuals"),
    "ETC": ("ETC", "etc", "estimate_to_complete", "remaining_cost"),
    "EAC": (
        "EAC",
        "eac",
        "estimate_at_completion",
        "forecast_at_completion",
    ),
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
    "pending_change_exposure": (
        "pending_change_exposure",
        "pending_changes",
        "unapproved_changes",
    ),
    "risk_exposure": (
        "risk_exposure",
        "quantified_risk",
        "emv",
        "configured_risk_uplift",
    ),
    "risk_adjusted_EAC": (
        "risk_adjusted_EAC",
        "risk_adjusted_eac",
        "P80_EAC",
        "p80_eac",
    ),
    "actual_start": ("actual_start", "act_start_date"),
    "actual_finish": ("actual_finish", "act_end_date"),
    "early_start": ("early_start", "early_start_date"),
    "early_finish": ("early_finish", "early_end_date"),
    "late_finish": ("late_finish", "late_end_date"),
    "original_duration_hours": (
        "original_duration_hours",
        "target_drtn_hr_cnt",
    ),
    "remaining_duration_hours": (
        "remaining_duration_hours",
        "remain_drtn_hr_cnt",
    ),
    "total_float_hours": ("total_float_hours", "total_float_hr_cnt"),
    "physical_percent_complete": (
        "physical_percent_complete",
        "phys_complete_pct",
    ),
    "status_code": ("status_code", "task_status"),
}


CATALOGUE: tuple[Equation, ...] = (
    Equation(
        "cost.eac_identity",
        "EAC equals actual cost plus ETC",
        "cost",
        "EAC == AC + ETC",
        "blocker",
        "The forecast at completion must reconcile to actual cost plus remaining forecast.",
        "Reconcile the cost ledger and forecast detail; do not post the close until the identity holds.",
        ("EAC", "AC", "ETC"),
    ),
    Equation(
        "cost.vac_identity",
        "VAC equals BAC minus EAC",
        "cost",
        "VAC == BAC - EAC",
        "major",
        "Variance at completion must agree with the approved budget and current EAC.",
        "Recalculate VAC from governed BAC and EAC.",
        ("VAC", "BAC", "EAC"),
    ),
    Equation(
        "evm.cv_identity",
        "Cost variance equals EV minus AC",
        "earned_value",
        "CV == EV - AC",
        "major",
        "Reported cost variance must reconcile to earned value and actual cost.",
        "Recalculate CV and investigate source-period or currency mismatches.",
        ("CV", "EV", "AC"),
    ),
    Equation(
        "evm.sv_identity",
        "Schedule variance equals EV minus PV",
        "earned_value",
        "SV == EV - PV",
        "major",
        "Reported schedule variance must reconcile to earned and planned value.",
        "Recalculate SV and verify the status date and baseline time-phasing.",
        ("SV", "EV", "PV"),
    ),
    Equation(
        "evm.cpi_identity",
        "CPI equals EV divided by AC",
        "earned_value",
        "CPI == EV / AC",
        "major",
        "The cost performance index must be derived from the same EV and AC basis.",
        "Recalculate CPI; verify zero-value, currency and accounting-period handling.",
        ("CPI", "EV", "AC"),
        tolerance=1e-4,
    ),
    Equation(
        "evm.spi_identity",
        "SPI equals EV divided by PV",
        "earned_value",
        "SPI == EV / PV",
        "major",
        "The schedule performance index must be derived from the same EV and PV basis.",
        "Recalculate SPI and verify baseline and status-period alignment.",
        ("SPI", "EV", "PV"),
        tolerance=1e-4,
    ),
    Equation(
        "change.budget_bridge",
        "Current budget bridges baseline and approved change",
        "change",
        "current_budget == baseline_budget + approved_changes",
        "blocker",
        "Current budget must be traceable to the baseline plus approved change.",
        "Locate unauthorized budget movement or missing approved change records.",
        ("current_budget", "baseline_budget", "approved_changes"),
    ),
    Equation(
        "risk.adjusted_bridge",
        "Risk-adjusted EAC bridges forecast, pending change and configured risk uplift",
        "risk",
        "risk_adjusted_EAC == EAC + pending_change_exposure + risk_exposure",
        "major",
        "The supplied risk-adjusted summary must reconcile to deterministic EAC, pending change and the configured risk uplift. This control validates a declared bridge; it does not calculate a statistical P80.",
        "Reconcile the risk register and pending-change log to the submitted risk-adjusted summary.",
        (
            "risk_adjusted_EAC",
            "EAC",
            "pending_change_exposure",
            "risk_exposure",
        ),
    ),
    Equation(
        "schedule.progress_duration",
        "In-progress activity retains remaining duration",
        "schedule",
        "remaining_duration_hours > 0",
        "major",
        "An in-progress activity should retain positive remaining duration.",
        "Correct activity status, actual finish or remaining duration in P6.",
        ("remaining_duration_hours",),
        record_type="activity",
        applicability_field="status_code",
        applicability_values=("progress", "active", "tk_active"),
    ),
    Equation(
        "schedule.extreme_negative_float",
        "Total float remains above the starter review threshold",
        "schedule",
        "total_float_hours >= -800",
        "minor",
        "The built-in -800 hour threshold is a conservative starter control for extreme negative float, not a contractual limit.",
        "Replace the starter threshold with a project-specific equation, then review constraints, calendars and driving relationships.",
        ("total_float_hours",),
        record_type="activity",
    ),
)


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


def _parse_expression(expression: str) -> ast.Compare:
    if not isinstance(expression, str) or not expression.strip():
        raise ControlsError("Equation expression must be a non-empty string")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ControlsError(
            f"Equation exceeds the {MAX_EXPRESSION_LENGTH}-character limit"
        )
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ControlsError(f"Invalid equation: {expression}") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_EXPRESSION_NODES:
        raise ControlsError("Equation is too complex")
    body = tree.body
    if (
        not isinstance(body, ast.Compare)
        or len(body.ops) != 1
        or len(body.comparators) != 1
    ):
        raise ControlsError("Equation must contain exactly one comparison")
    if not isinstance(body.ops[0], (ast.Eq, ast.LtE, ast.GtE, ast.Lt, ast.Gt)):
        raise ControlsError("Only ==, <=, >=, < and > are supported")
    allowed = (
        ast.Expression,
        ast.Compare,
        ast.Eq,
        ast.LtE,
        ast.GtE,
        ast.Lt,
        ast.Gt,
        ast.BinOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.UnaryOp,
        ast.UAdd,
        ast.USub,
        ast.Call,
        ast.Name,
        ast.Load,
        ast.Constant,
    )
    for node in nodes:
        if not isinstance(node, allowed):
            raise ControlsError("Unsupported equation syntax")
        if isinstance(node, ast.Constant) and (
            not isinstance(node.value, (int, float))
            or isinstance(node.value, bool)
        ):
            raise ControlsError("Equation constants must be numeric")
        if isinstance(node, ast.Call):
            if (
                not isinstance(node.func, ast.Name)
                or node.func.id not in _ALLOWED_FUNCTIONS
            ):
                raise ControlsError("Unsupported equation function")
            if node.keywords:
                raise ControlsError("Keyword arguments are not supported")
            argc = len(node.args)
            if node.func.id == "abs" and argc != 1:
                raise ControlsError("abs() requires exactly one argument")
            if node.func.id == "round" and argc not in (1, 2):
                raise ControlsError("round() requires one or two arguments")
            if node.func.id in {"min", "max"} and argc < 1:
                raise ControlsError(
                    f"{node.func.id}() requires at least one argument"
                )
    return body


def _expression_fields(expression: str) -> set[str]:
    body = _parse_expression(expression)
    functions = {
        node.func.id
        for node in ast.walk(body)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    return {
        node.id for node in ast.walk(body) if isinstance(node, ast.Name)
    } - functions


def _eval(node: ast.AST, values: Mapping[str, float]) -> float:
    if isinstance(node, ast.Constant):
        return _number(node.value, "constant")
    if isinstance(node, ast.Name):
        if node.id not in values:
            raise KeyError(node.id)
        return values[node.id]
    if isinstance(node, ast.UnaryOp):
        value = _eval(node.operand, values)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp):
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
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        args = [_eval(arg, values) for arg in node.args]
        if node.func.id == "round" and len(args) == 2:
            return float(round(args[0], int(args[1])))
        return float(_ALLOWED_FUNCTIONS[node.func.id](*args))
    raise ControlsError("Unsupported equation syntax")


def evaluate(
    expression: str,
    values: Mapping[str, float],
    tolerance: float,
) -> tuple[bool, float]:
    tolerance = _number(tolerance, "tolerance")
    if tolerance < 0:
        raise ControlsError("tolerance must be non-negative")
    body = _parse_expression(expression)
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
    if "risk_adjusted_EAC" in normalized:
        normalized.setdefault("P80_EAC", normalized["risk_adjusted_EAC"])
    elif "P80_EAC" in normalized:
        normalized["risk_adjusted_EAC"] = normalized["P80_EAC"]
    return normalized


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(
    path: str | Path,
    record_type: str = "control_account",
) -> list[dict[str, Any]]:
    if record_type not in RECORD_TYPES:
        raise ControlsError(f"Unsupported record type: {record_type}")
    source = Path(path)
    digest = _sha256(source)
    with source.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ControlsError(f"{source.name} does not contain a CSV header")
        rows = []
        for index, row in enumerate(reader, start=2):
            if len(rows) >= MAX_CSV_ROWS:
                raise ControlsError(
                    f"{source.name} exceeds the {MAX_CSV_ROWS:,}-row safety limit"
                )
            normalized = normalize_row(row)
            normalized["_record_type"] = record_type
            normalized["_source"] = source.name
            normalized["_source_sha256"] = digest
            normalized["_row"] = index
            rows.append(normalized)
    if not rows:
        raise ControlsError(f"{source.name} does not contain any data rows")
    return rows


def parse_xer(path: str | Path) -> list[dict[str, Any]]:
    """Parse Primavera P6 XER TASK records into canonical activity rows."""
    source = Path(path)
    digest = _sha256(source)
    table = ""
    fields: list[str] = []
    activities: list[dict[str, Any]] = []
    with source.open(encoding="utf-8-sig", errors="replace") as handle:
        for raw in handle:
            parts = raw.rstrip("\r\n").split("\t")
            marker = parts[0] if parts else ""
            if marker == "%T":
                table = parts[1] if len(parts) > 1 else ""
                fields = []
            elif marker == "%F":
                fields = parts[1:]
            elif marker == "%R" and table == "TASK" and fields:
                if len(activities) >= MAX_XER_ROWS:
                    raise ControlsError(
                        f"{source.name} exceeds the {MAX_XER_ROWS:,}-activity safety limit"
                    )
                values = parts[1:] + [""] * max(
                    0,
                    len(fields) - len(parts[1:]),
                )
                row = dict(zip(fields, values))
                normalized = normalize_row(row)
                normalized["record_id"] = (
                    row.get("task_code") or row.get("task_id") or "unknown"
                )
                normalized["activity_name"] = row.get("task_name", "")
                normalized["wbs_id"] = row.get("wbs_id", "")
                normalized["_record_type"] = "activity"
                normalized["_source"] = source.name
                normalized["_source_sha256"] = digest
                activities.append(normalized)
    if not activities:
        raise ControlsError("No TASK records were found in the P6 XER")
    return activities


def parse_equations(document: Any) -> tuple[Equation, ...]:
    if not isinstance(document, list):
        raise ControlsError("Equation pack must be a JSON array")
    if len(document) > MAX_EQUATIONS:
        raise ControlsError(
            f"Equation pack exceeds the {MAX_EQUATIONS}-equation limit"
        )
    equations: list[Equation] = []
    seen: set[str] = set()
    for index, item in enumerate(document, start=1):
        label = f"equation {index}"
        if not isinstance(item, dict):
            raise ControlsError(f"{label} must be an object")
        unknown = set(item) - _ALLOWED_DOCUMENT_FIELDS
        if unknown:
            raise ControlsError(
                f"{label} contains unknown fields: {', '.join(sorted(unknown))}"
            )
        equation_id = item.get("id")
        if (
            not isinstance(equation_id, str)
            or not _EQUATION_ID.fullmatch(equation_id)
        ):
            raise ControlsError(
                f"{label}.id must be a stable identifier of at most 128 characters"
            )
        if equation_id in seen:
            raise ControlsError(f"Duplicate equation id: {equation_id}")
        seen.add(equation_id)
        expression = item.get("expression")
        if not isinstance(expression, str):
            raise ControlsError(f"{equation_id}.expression must be a string")
        required = item.get("required_fields", [])
        if (
            not isinstance(required, list)
            or not required
            or not all(isinstance(value, str) for value in required)
        ):
            raise ControlsError(
                f"{equation_id}.required_fields must be a non-empty string array"
            )
        if len(set(required)) != len(required):
            raise ControlsError(
                f"{equation_id}.required_fields contains duplicates"
            )
        for field in required:
            if not field.isidentifier() or keyword.iskeyword(field):
                raise ControlsError(
                    f"{equation_id} contains an invalid field name: {field}"
                )
        missing = _expression_fields(expression) - set(required)
        if missing:
            raise ControlsError(
                f"{equation_id}.required_fields is missing expression fields: {', '.join(sorted(missing))}"
            )
        severity = str(item.get("severity", "major"))
        if severity not in SEVERITIES:
            raise ControlsError(
                f"{equation_id}.severity must be one of: {', '.join(SEVERITIES)}"
            )
        record_type = str(item.get("record_type", "control_account"))
        if record_type not in RECORD_TYPES:
            raise ControlsError(
                f"{equation_id}.record_type must be one of: {', '.join(RECORD_TYPES)}"
            )
        tolerance = _number(
            item.get("tolerance", 1e-6),
            f"{equation_id}.tolerance",
        )
        if tolerance < 0:
            raise ControlsError(
                f"{equation_id}.tolerance must be non-negative"
            )
        applies = item.get("applies_when")
        applicability_field: str | None = None
        applicability_values: tuple[str, ...] = ()
        if applies is not None:
            if (
                not isinstance(applies, dict)
                or set(applies) != {"field", "contains_any"}
            ):
                raise ControlsError(
                    f"{equation_id}.applies_when must contain exactly field and contains_any"
                )
            applicability_field = applies["field"]
            values = applies["contains_any"]
            if (
                not isinstance(applicability_field, str)
                or not applicability_field
            ):
                raise ControlsError(
                    f"{equation_id}.applies_when.field must be a string"
                )
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) and value for value in values)
            ):
                raise ControlsError(
                    f"{equation_id}.applies_when.contains_any must be a non-empty string array"
                )
            applicability_values = tuple(
                value.casefold() for value in values
            )
        title = item.get("title", equation_id)
        if not isinstance(title, str) or not title.strip():
            raise ControlsError(
                f"{equation_id}.title must be a non-empty string"
            )
        equations.append(
            Equation(
                id=equation_id,
                title=title.strip(),
                domain=str(item.get("domain", "custom")).strip()
                or "custom",
                expression=expression.strip(),
                severity=severity,
                description=str(item.get("description", "")).strip(),
                remediation=str(
                    item.get(
                        "remediation",
                        "Review the source data and equation.",
                    )
                ).strip(),
                required_fields=tuple(required),
                tolerance=tolerance,
                record_type=record_type,
                applicability_field=applicability_field,
                applicability_values=applicability_values,
            )
        )
    return tuple(equations)


def load_equations(path: str | Path) -> tuple[Equation, ...]:
    return parse_equations(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def validate_equation_set(
    equations: Sequence[Equation],
) -> tuple[Equation, ...]:
    if len(equations) > MAX_EQUATIONS:
        raise ControlsError(
            f"Analysis exceeds the {MAX_EQUATIONS}-equation limit"
        )
    seen: set[str] = set()
    for equation in equations:
        if equation.id in seen:
            raise ControlsError(f"Duplicate equation id: {equation.id}")
        seen.add(equation.id)
        if equation.severity not in SEVERITIES:
            raise ControlsError(
                f"Unsupported severity on {equation.id}: {equation.severity}"
            )
        if equation.record_type not in RECORD_TYPES:
            raise ControlsError(
                f"Unsupported record type on {equation.id}: {equation.record_type}"
            )
        missing = _expression_fields(equation.expression) - set(
            equation.required_fields
        )
        if missing:
            raise ControlsError(
                f"{equation.id}.required_fields is missing expression fields: {', '.join(sorted(missing))}"
            )
    return tuple(equations)


def _coerce_values(
    row: Mapping[str, Any],
    fields: Sequence[str],
) -> dict[str, float] | None:
    output: dict[str, float] = {}
    for field in fields:
        value = row.get(field)
        if value in (None, ""):
            return None
        try:
            output[field] = _number(value, field)
        except ControlsError:
            return None
    return output


def _source_manifest(
    records: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    counts: Counter[tuple[str, str, str]] = Counter()
    for row in records:
        name = Path(str(row.get("_source", "supplied-records"))).name
        digest = str(row.get("_source_sha256", ""))
        record_type = str(row.get("_record_type", "control_account"))
        counts[(name, digest, record_type)] += 1
    return tuple(
        {
            "name": name,
            "sha256": digest or None,
            "record_type": record_type,
            "records": count,
        }
        for (name, digest, record_type), count in sorted(counts.items())
    )


def analyze(
    records: Sequence[Mapping[str, Any]],
    *,
    equations: Sequence[Equation] = CATALOGUE,
    sources: Iterable[str] = (),
) -> Analysis:
    validated = validate_equation_set(tuple(equations))
    findings: list[Finding] = []
    executed = 0
    for raw in records:
        row = normalize_row(raw)
        record_type = str(row.get("_record_type", "control_account"))
        record_id = str(
            row.get("record_id")
            or row.get("task_code")
            or row.get("_row")
            or "unknown"
        )
        for equation in validated:
            if equation.record_type != record_type:
                continue
            if equation.applicability_field:
                observed = str(
                    row.get(equation.applicability_field, "")
                ).casefold()
                if not any(
                    token in observed
                    for token in equation.applicability_values
                ):
                    findings.append(
                        Finding(
                            equation.id,
                            equation.title,
                            equation.domain,
                            equation.severity,
                            record_type,
                            record_id,
                            "not_applicable",
                            0.0,
                            equation.expression,
                            equation.description,
                            equation.remediation,
                            {},
                        )
                    )
                    continue
            values = _coerce_values(row, equation.required_fields)
            if values is None:
                findings.append(
                    Finding(
                        equation.id,
                        equation.title,
                        equation.domain,
                        equation.severity,
                        record_type,
                        record_id,
                        "not_applicable",
                        0.0,
                        equation.expression,
                        equation.description,
                        equation.remediation,
                        {},
                    )
                )
                continue
            executed += 1
            try:
                passed, residual = evaluate(
                    equation.expression,
                    values,
                    equation.tolerance,
                )
                status = "pass" if passed else "fail"
            except (ZeroDivisionError, OverflowError):
                status, residual = "fail", math.inf
            findings.append(
                Finding(
                    equation.id,
                    equation.title,
                    equation.domain,
                    equation.severity,
                    record_type,
                    record_id,
                    status,
                    residual,
                    equation.expression,
                    equation.description,
                    equation.remediation,
                    values,
                )
            )
    findings.sort(
        key=lambda item: (
            0
            if item.status == "fail"
            else 1
            if item.status == "pass"
            else 2,
            SEVERITY_RANK.get(item.severity, 9),
            -abs(item.residual)
            if math.isfinite(item.residual)
            else float("-inf"),
            item.record_id,
            item.equation_id,
        )
    )
    source_names = tuple(
        dict.fromkeys(Path(str(source)).name for source in sources)
    )
    manifest = _source_manifest(records)
    if not source_names:
        source_names = tuple(item["name"] for item in manifest)
    return Analysis(
        sources=source_names,
        source_manifest=manifest,
        records_analyzed=len(records),
        equations_considered=len(validated),
        equations_executed=executed,
        findings=tuple(findings),
        equations=validated,
    )


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _csv_safe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.replace("\r", " ").replace("\n", " ")
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def render_markdown(analysis: Analysis) -> str:
    rows = []
    for finding in analysis.failures:
        residual = (
            "non-finite"
            if not math.isfinite(finding.residual)
            else f"{finding.residual:.6g}"
        )
        rows.append(
            "| "
            + " | ".join(
                (
                    f"`{_markdown_cell(finding.severity)}`",
                    f"`{_markdown_cell(finding.record_id)}`",
                    f"`{_markdown_cell(finding.equation_id)}`",
                    f"`{residual}`",
                    _markdown_cell(finding.remediation),
                )
            )
            + " |"
        )
    exceptions = (
        "\n".join(rows)
        or "| — | — | — | — | No exceptions |"
    )
    gate_label = {
        "blocked": "BLOCKED",
        "review": "REVIEW REQUIRED",
        "ready": "READY",
    }[analysis.gate_status]
    return f"""# EQ-Proof Project Controls Assurance Report

## Close gate

| Metric | Value |
| --- | ---: |
| Gate | **{gate_label}** |
| Records analyzed | {analysis.records_analyzed} |
| Equations executed | {analysis.equations_executed} |
| Blockers | {len(analysis.blockers)} |
| Total failures | {len(analysis.failures)} |

## Ranked exception register

| Severity | Record | Equation | Residual | Required action |
| --- | --- | --- | ---: | --- |
{exceptions}

## Operating boundary

The workbench evaluates supplied exports against declared equations. It does not approve changes, infer contractual truth, or convert schedule defects into monetary impacts without an explicit user equation. The output embeds the complete equation manifest and source digests when files were loaded through the native adapters.
"""


def write_outputs(analysis: Analysis, directory: str | Path) -> None:
    output = Path(directory)
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(
        json.dumps(
            analysis.to_dict(),
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (output / "report.md").write_text(
        render_markdown(analysis),
        encoding="utf-8",
    )
    with (output / "exceptions.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "severity",
                "record_type",
                "record_id",
                "equation_id",
                "residual",
                "residual_state",
                "remediation",
            ]
        )
        for item in analysis.failures:
            writer.writerow(
                [
                    _csv_safe(item.severity),
                    _csv_safe(item.record_type),
                    _csv_safe(item.record_id),
                    _csv_safe(item.equation_id),
                    item.residual if math.isfinite(item.residual) else "",
                    "finite"
                    if math.isfinite(item.residual)
                    else "non_finite",
                    _csv_safe(item.remediation),
                ]
            )
