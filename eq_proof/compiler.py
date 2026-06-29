from __future__ import annotations

import re
from typing import Dict, Iterable, List

from .linear import RELATION_RE, as_float, compile_linear_relation, is_simple_number, symbol_names_from_text
from .spec import Spec


COMMENT_RE = re.compile(r"#.*$")
CALL_RE = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)\((?P<args>.*)\)$")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _items(text: str) -> List[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _clean_lines(text_or_lines: str | Iterable[str]) -> List[str]:
    if isinstance(text_or_lines, str):
        raw_lines: List[str] = []
        for line in text_or_lines.splitlines():
            raw_lines.extend(line.split(";"))
    else:
        raw_lines = list(text_or_lines)
    lines = []
    for raw in raw_lines:
        line = COMMENT_RE.sub("", raw).strip()
        if line:
            lines.append(line)
    return lines


def _declared_variables(line: str) -> List[str] | None:
    match = re.match(r"^(variables|vars)\s*:\s*(.+)$", line, flags=re.IGNORECASE)
    if not match:
        return None
    return _items(match.group(2))


def _unit_declaration(line: str) -> tuple[str, str] | None:
    match = re.match(r"^unit\s+([A-Za-z_][A-Za-z0-9_]*)\s*[:=]\s*(.+)$", line, flags=re.IGNORECASE)
    if match:
        return match.group(1), match.group(2).strip()
    match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\[(.+)\]$", line)
    if match:
        return match.group(1), match.group(2).strip()
    return None


def _call(line: str) -> tuple[str, List[str]] | None:
    match = CALL_RE.match(line)
    if not match:
        return None
    return match.group("name").lower(), _items(match.group("args"))


def _relations_from_chain(line: str) -> List[str] | None:
    matches = list(RELATION_RE.finditer(line))
    if len(matches) != 2:
        return None
    parts = [
        line[: matches[0].start()].strip(),
        line[matches[0].end() : matches[1].start()].strip(),
        line[matches[1].end() :].strip(),
    ]
    ops = [matches[0].group(0), matches[1].group(0)]
    if ops == ["<=", "<="]:
        return [f"{parts[0]} <= {parts[1]}", f"{parts[1]} <= {parts[2]}"]
    if ops == [">=", ">="]:
        return [f"{parts[1]} <= {parts[0]}", f"{parts[2]} <= {parts[1]}"]
    raise ValueError(f"Mixed chained relation is ambiguous: {line!r}")


def _bounds_constraint(relation: str) -> Dict | None:
    parts = [p.strip() for p in RELATION_RE.split(relation)]
    ops = [m.group(0) for m in RELATION_RE.finditer(relation)]
    if len(parts) != 2 or len(ops) != 1:
        return None
    left, right = parts
    op = ops[0]
    if op == "==":
        op = "="

    if op == "<=" and IDENT_RE.match(left) and is_simple_number(right):
        return {"type": "bounds", "var": left, "lower": None, "upper": as_float(right)}
    if op == ">=" and IDENT_RE.match(left) and is_simple_number(right):
        return {"type": "bounds", "var": left, "lower": as_float(right), "upper": None}
    if op == "<=" and is_simple_number(left) and IDENT_RE.match(right):
        return {"type": "bounds", "var": right, "lower": as_float(left), "upper": None}
    if op == ">=" and is_simple_number(left) and IDENT_RE.match(right):
        return {"type": "bounds", "var": right, "lower": None, "upper": as_float(left)}
    return None


def _merge_bounds(constraints: List[Dict]) -> List[Dict]:
    merged: Dict[str, Dict] = {}
    out: List[Dict] = []
    for constraint in constraints:
        if constraint.get("type") != "bounds":
            out.append(constraint)
            continue
        var = constraint["var"]
        current = merged.setdefault(var, {"type": "bounds", "var": var, "lower": None, "upper": None})
        if constraint.get("lower") is not None:
            lower = float(constraint["lower"])
            current["lower"] = lower if current["lower"] is None else max(float(current["lower"]), lower)
        if constraint.get("upper") is not None:
            upper = float(constraint["upper"])
            current["upper"] = upper if current["upper"] is None else min(float(current["upper"]), upper)
    return list(merged.values()) + out


def compile_written_constraints(
    text_or_lines: str | Iterable[str],
    *,
    name: str = "written_constraints",
    version: str = "1.0",
    units: Dict[str, str] | None = None,
    fixed: Iterable[str] | None = None,
) -> Spec:
    constraints: List[Dict] = []
    variables: List[str] = []
    units_map: Dict[str, str] = dict(units or {})
    fixed_vars = list(fixed or [])

    def add_var(var: str) -> None:
        if var not in variables:
            variables.append(var)

    for line in _clean_lines(text_or_lines):
        declared = _declared_variables(line)
        if declared is not None:
            for var in declared:
                add_var(var)
            continue

        unit_decl = _unit_declaration(line)
        if unit_decl is not None:
            var, unit = unit_decl
            add_var(var)
            units_map[var] = unit
            continue

        call = _call(line)
        if call is not None:
            cname, args = call
            if cname == "simplex":
                constraints.append({"type": "simplex", "vars": args})
                for var in args:
                    add_var(var)
                continue
            if cname == "monotone":
                constraints.append({"type": "monotone", "vars": args})
                for var in args:
                    add_var(var)
                continue
            if cname in ("fixed", "fix", "constant"):
                for var in args:
                    add_var(var)
                    if var not in fixed_vars:
                        fixed_vars.append(var)
                continue

        chained = _relations_from_chain(line)
        relation_lines = chained if chained is not None else [line]

        pending = list(relation_lines)
        while pending:
            relation_line = pending.pop(0)
            relation_match = list(RELATION_RE.finditer(relation_line))
            if len(relation_match) != 1:
                raise ValueError(f"Expected one relation in {relation_line!r}")
            match = relation_match[0]
            left = relation_line[: match.start()].strip()
            op = match.group(0)
            right = relation_line[match.end() :].strip()

            if "," in left and op in ("<=", ">=", "=", "=="):
                for item in _items(left):
                    pending.append(f"{item} {op} {right}")
                continue

            bounds = _bounds_constraint(relation_line)
            if bounds is not None:
                constraints.append(bounds)
                add_var(bounds["var"])
                continue

            relation = compile_linear_relation(relation_line)
            if relation.op == "=":
                constraints.append(
                    {
                        "type": "linear_eq",
                        "coeffs": relation.coeffs,
                        "rhs": relation.rhs,
                        "expr": relation.source,
                    }
                )
            else:
                constraints.append(
                    {
                        "type": "linear_leq",
                        "coeffs": relation.coeffs,
                        "rhs": relation.rhs,
                        "expr": relation.source,
                    }
                )
            for var in relation.coeffs:
                add_var(var)
            for var in symbol_names_from_text(relation_line):
                add_var(var)

    for var in variables:
        units_map.setdefault(var, "1")
    return Spec(name, version, variables, _merge_bounds(constraints), [], [], units_map, fixed_vars)


def spec_to_dict(spec: Spec) -> Dict:
    return {
        "name": spec.name,
        "version": spec.version,
        "variables": spec.variables,
        "constraints": spec.constraints,
        "probes": spec.probes,
        "alternates": spec.alternates,
        "units": spec.units,
        "fixed": spec.fixed,
    }
