"""Specification parsing, semantic validation, and file loading."""

from __future__ import annotations

import json
import keyword
import math
from pathlib import Path
from typing import Any

from .compiler import compile_equation
from .domain import LinearConstraint, Specification, VariableRule
from .errors import InvalidSpecification

SCHEMA_VERSION = "1.0"
_ROOT_KEYS = {"schema_version", "name", "description", "variables", "equations", "metadata"}
_VARIABLE_KEYS = {"lower", "upper", "fixed", "label", "unit"}
_EQUATION_KEYS = {"id", "expression", "description"}


def _reject_unknown_keys(document: dict[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(document) - allowed)
    if unknown:
        raise InvalidSpecification(f"Unknown {label} field(s): {', '.join(unknown)}")


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidSpecification(f"{label} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidSpecification(f"{label} must be finite")
    return numeric


def _optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InvalidSpecification(f"{label} must be a non-empty string when provided")
    return value.strip()


def parse_specification(document: dict[str, Any]) -> Specification:
    if not isinstance(document, dict):
        raise InvalidSpecification("Specification root must be a JSON object")
    _reject_unknown_keys(document, _ROOT_KEYS, "root")

    version = document.get("schema_version")
    if version != SCHEMA_VERSION:
        raise InvalidSpecification(
            f"Unsupported schema_version {version!r}; expected {SCHEMA_VERSION!r}"
        )
    name = document.get("name")
    if not isinstance(name, str) or not name.strip():
        raise InvalidSpecification("Specification name must be a non-empty string")
    description = document.get("description", "")
    if not isinstance(description, str):
        raise InvalidSpecification("Specification description must be a string")
    metadata = document.get("metadata", {})
    if not isinstance(metadata, dict):
        raise InvalidSpecification("Specification metadata must be an object")

    raw_variables = document.get("variables")
    if not isinstance(raw_variables, dict) or not raw_variables:
        raise InvalidSpecification("variables must be a non-empty object")

    variables: list[VariableRule] = []
    for variable_name, rule in raw_variables.items():
        if (
            not isinstance(variable_name, str)
            or not variable_name.isidentifier()
            or keyword.iskeyword(variable_name)
        ):
            raise InvalidSpecification(f"Invalid variable name: {variable_name!r}")
        if not isinstance(rule, dict):
            raise InvalidSpecification(f"Variable rule for {variable_name} must be an object")
        _reject_unknown_keys(rule, _VARIABLE_KEYS, f"variable {variable_name}")
        lower = _finite(rule["lower"], f"{variable_name}.lower") if "lower" in rule else None
        upper = _finite(rule["upper"], f"{variable_name}.upper") if "upper" in rule else None
        if lower is not None and upper is not None and lower > upper:
            raise InvalidSpecification(f"Lower bound exceeds upper bound for {variable_name}")
        fixed = rule.get("fixed", False)
        if not isinstance(fixed, bool):
            raise InvalidSpecification(f"{variable_name}.fixed must be boolean")
        variables.append(
            VariableRule(
                variable_name,
                lower,
                upper,
                fixed,
                _optional_text(rule.get("label"), f"{variable_name}.label"),
                _optional_text(rule.get("unit"), f"{variable_name}.unit"),
            )
        )

    variable_names = tuple(variable.name for variable in variables)
    raw_equations = document.get("equations", [])
    if not isinstance(raw_equations, list):
        raise InvalidSpecification("equations must be an array")

    constraints: list[LinearConstraint] = []
    identifiers: set[str] = set()
    for index, item in enumerate(raw_equations, start=1):
        if not isinstance(item, dict):
            raise InvalidSpecification(f"Equation #{index} must be an object")
        _reject_unknown_keys(item, _EQUATION_KEYS, f"equation #{index}")
        identifier = item.get("id", f"equation-{index}")
        expression = item.get("expression")
        if not isinstance(identifier, str) or not identifier.strip():
            raise InvalidSpecification(f"Equation #{index} id must be a non-empty string")
        identifier = identifier.strip()
        if identifier in identifiers:
            raise InvalidSpecification(f"Duplicate equation id: {identifier}")
        identifiers.add(identifier)
        if not isinstance(expression, str) or not expression.strip():
            raise InvalidSpecification(f"Equation {identifier} needs a non-empty expression")
        description_value = item.get("description", "")
        if not isinstance(description_value, str):
            raise InvalidSpecification(f"Equation {identifier} description must be a string")
        coefficients, relation, rhs = compile_equation(expression, variable_names)
        constraints.append(
            LinearConstraint(
                identifier,
                coefficients,
                relation,
                rhs,
                expression.strip(),
                description_value,
            )
        )

    return Specification(
        schema_version=version,
        name=name.strip(),
        description=description,
        variables=tuple(variables),
        constraints=tuple(constraints),
        source_document=document,
    )


def load_specification(path: str | Path) -> Specification:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InvalidSpecification(f"Unable to read specification {path}: {exc}") from exc
    return parse_specification(document)
