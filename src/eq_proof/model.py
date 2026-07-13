"""EQ-Proof core: safe linear compilation, validation, diagnostics, and projection."""

from __future__ import annotations

import ast
import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

class EQProofError(Exception):
    """Base class for expected EQ-Proof failures."""


class InvalidSpecification(EQProofError):
    """The specification is malformed, unsafe, or unsupported."""


class InfeasibleProblem(EQProofError):
    """No feasible repair was found for the submitted problem."""


class InvalidProof(EQProofError):
    """The proof artifact is malformed or fails verification."""


Relation = Literal["==", "<="]


@dataclass(frozen=True)
class VariableRule:
    name: str
    lower: float | None = None
    upper: float | None = None
    fixed: bool = False


@dataclass(frozen=True)
class LinearConstraint:
    identifier: str
    coefficients: tuple[float, ...]
    relation: Relation
    rhs: float
    source: str


@dataclass(frozen=True)
class Specification:
    schema_version: str
    name: str
    description: str
    variables: tuple[VariableRule, ...]
    constraints: tuple[LinearConstraint, ...]
    source_document: dict[str, Any]

    @property
    def variable_names(self) -> tuple[str, ...]:
        return tuple(variable.name for variable in self.variables)


@dataclass(frozen=True)
class ConstraintCheck:
    identifier: str
    source: str
    relation: str
    lhs: float
    rhs: float
    violation: float
    satisfied: bool


@dataclass(frozen=True)
class RepairResult:
    status: Literal["already_feasible", "repaired"]
    submitted: dict[str, float]
    repaired: dict[str, float]
    movement_l2: float
    iterations: int
    tolerance: float
    max_violation_before: float
    max_violation_after: float
    checks_before: tuple[ConstraintCheck, ...] = field(default_factory=tuple)
    checks_after: tuple[ConstraintCheck, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProofResult:
    proof: dict[str, Any]
    verified: bool
    signer_fingerprint: str | None


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


@dataclass(frozen=True)
class LinearForm:
    coefficients: dict[str, float]
    constant: float = 0.0

    def add(self, other: "LinearForm", scale: float = 1.0) -> "LinearForm":
        merged = dict(self.coefficients)
        for name, value in other.coefficients.items():
            merged[name] = merged.get(name, 0.0) + scale * value
            if abs(merged[name]) < 1e-15:
                del merged[name]
        return LinearForm(merged, self.constant + scale * other.constant)

    def scaled(self, factor: float) -> "LinearForm":
        return LinearForm(
            {name: factor * value for name, value in self.coefficients.items()},
            factor * self.constant,
        )


def _number(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return float(node.value)
    raise InvalidSpecification("Only finite numeric constants are allowed in equations")


def _linearize(node: ast.AST, variables: set[str]) -> LinearForm:
    if isinstance(node, ast.Name):
        if node.id not in variables:
            raise InvalidSpecification(f"Unknown variable in equation: {node.id}")
        return LinearForm({node.id: 1.0})
    if isinstance(node, ast.Constant):
        return LinearForm({}, _number(node))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        form = _linearize(node.operand, variables)
        return form if isinstance(node.op, ast.UAdd) else form.scaled(-1.0)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        left = _linearize(node.left, variables)
        right = _linearize(node.right, variables)
        return left.add(right, -1.0 if isinstance(node.op, ast.Sub) else 1.0)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        try:
            factor = _number(node.left)
            return _linearize(node.right, variables).scaled(factor)
        except InvalidSpecification:
            factor = _number(node.right)
            return _linearize(node.left, variables).scaled(factor)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        divisor = _number(node.right)
        if divisor == 0:
            raise InvalidSpecification("Division by zero in equation")
        return _linearize(node.left, variables).scaled(1.0 / divisor)
    raise InvalidSpecification(
        "Unsupported expression. Use variables, finite numbers, +, -, scalar *, scalar /, and parentheses"
    )


def compile_equation(expression: str, variable_names: tuple[str, ...]) -> tuple[tuple[float, ...], str, float]:
    """Compile ``a + 2*b <= 4`` into a normalized linear constraint."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise InvalidSpecification(f"Invalid equation syntax: {expression}") from exc
    if not isinstance(tree.body, ast.Compare) or len(tree.body.ops) != 1 or len(tree.body.comparators) != 1:
        raise InvalidSpecification("Each equation must contain exactly one comparison")

    op = tree.body.ops[0]
    if not isinstance(op, (ast.Eq, ast.LtE, ast.GtE)):
        raise InvalidSpecification("Only ==, <=, and >= relations are supported")

    variables = set(variable_names)
    left = _linearize(tree.body.left, variables)
    right = _linearize(tree.body.comparators[0], variables)
    normalized = left.add(right, -1.0)
    rhs = -normalized.constant
    coefficients = tuple(normalized.coefficients.get(name, 0.0) for name in variable_names)

    if all(abs(value) < 1e-15 for value in coefficients):
        relation_true = abs(rhs) <= 1e-15 if isinstance(op, ast.Eq) else (
            0.0 <= rhs if isinstance(op, ast.LtE) else 0.0 >= rhs
        )
        if not relation_true:
            raise InvalidSpecification(f"Equation is contradictory: {expression}")
        raise InvalidSpecification(f"Equation has no variables and adds no constraint: {expression}")

    if isinstance(op, ast.Eq):
        return coefficients, "==", rhs
    if isinstance(op, ast.GtE):
        return tuple(-value for value in coefficients), "<=", -rhs
    return coefficients, "<=", rhs


SCHEMA_VERSION = "1.0"


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidSpecification(f"{label} must be a finite number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise InvalidSpecification(f"{label} must be finite")
    return numeric


def parse_specification(document: dict[str, Any]) -> Specification:
    if not isinstance(document, dict):
        raise InvalidSpecification("Specification root must be a JSON object")
    version = str(document.get("schema_version", ""))
    if version != SCHEMA_VERSION:
        raise InvalidSpecification(f"Unsupported schema_version {version!r}; expected {SCHEMA_VERSION!r}")
    name = document.get("name")
    if not isinstance(name, str) or not name.strip():
        raise InvalidSpecification("Specification name must be a non-empty string")
    description = document.get("description", "")
    if not isinstance(description, str):
        raise InvalidSpecification("Specification description must be a string")

    raw_variables = document.get("variables")
    if not isinstance(raw_variables, dict) or not raw_variables:
        raise InvalidSpecification("variables must be a non-empty object")

    variables: list[VariableRule] = []
    for variable_name, rule in raw_variables.items():
        if not isinstance(variable_name, str) or not variable_name.isidentifier():
            raise InvalidSpecification(f"Invalid variable name: {variable_name!r}")
        if not isinstance(rule, dict):
            raise InvalidSpecification(f"Variable rule for {variable_name} must be an object")
        lower = _finite(rule["lower"], f"{variable_name}.lower") if "lower" in rule else None
        upper = _finite(rule["upper"], f"{variable_name}.upper") if "upper" in rule else None
        if lower is not None and upper is not None and lower > upper:
            raise InvalidSpecification(f"Lower bound exceeds upper bound for {variable_name}")
        fixed = rule.get("fixed", False)
        if not isinstance(fixed, bool):
            raise InvalidSpecification(f"{variable_name}.fixed must be boolean")
        variables.append(VariableRule(variable_name, lower, upper, fixed))

    variable_names = tuple(variable.name for variable in variables)
    raw_equations = document.get("equations", [])
    if not isinstance(raw_equations, list):
        raise InvalidSpecification("equations must be an array")

    constraints: list[LinearConstraint] = []
    identifiers: set[str] = set()
    for index, item in enumerate(raw_equations, start=1):
        if not isinstance(item, dict):
            raise InvalidSpecification(f"Equation #{index} must be an object")
        identifier = item.get("id", f"equation-{index}")
        expression = item.get("expression")
        if not isinstance(identifier, str) or not identifier.strip():
            raise InvalidSpecification(f"Equation #{index} id must be a non-empty string")
        if identifier in identifiers:
            raise InvalidSpecification(f"Duplicate equation id: {identifier}")
        identifiers.add(identifier)
        if not isinstance(expression, str) or not expression.strip():
            raise InvalidSpecification(f"Equation {identifier} needs a non-empty expression")
        coefficients, relation, rhs = compile_equation(expression, variable_names)
        constraints.append(LinearConstraint(identifier, coefficients, relation, rhs, expression))

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


def checks(specification: Specification, vector: np.ndarray, tolerance: float) -> tuple[ConstraintCheck, ...]:
    output: list[ConstraintCheck] = []
    names = specification.variable_names

    for index, variable in enumerate(specification.variables):
        value = float(vector[index])
        if variable.lower is not None:
            violation = max(0.0, variable.lower - value)
            output.append(ConstraintCheck(
                f"bound:{variable.name}:lower", f"{variable.name} >= {variable.lower}", ">=", value,
                variable.lower, violation, violation <= tolerance,
            ))
        if variable.upper is not None:
            violation = max(0.0, value - variable.upper)
            output.append(ConstraintCheck(
                f"bound:{variable.name}:upper", f"{variable.name} <= {variable.upper}", "<=", value,
                variable.upper, violation, violation <= tolerance,
            ))

    for constraint in specification.constraints:
        lhs = float(np.dot(np.asarray(constraint.coefficients, dtype=float), vector))
        violation = abs(lhs - constraint.rhs) if constraint.relation == "==" else max(0.0, lhs - constraint.rhs)
        output.append(ConstraintCheck(
            constraint.identifier,
            constraint.source,
            constraint.relation,
            lhs,
            constraint.rhs,
            violation,
            violation <= tolerance,
        ))

    return tuple(output)


def max_violation(items: tuple[ConstraintCheck, ...]) -> float:
    return max((item.violation for item in items), default=0.0)


def as_dict(item: ConstraintCheck) -> dict[str, object]:
    return {
        "id": item.identifier,
        "source": item.source,
        "relation": item.relation,
        "lhs": item.lhs,
        "rhs": item.rhs,
        "violation": item.violation,
        "satisfied": item.satisfied,
    }
