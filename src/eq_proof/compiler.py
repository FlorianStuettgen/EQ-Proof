"""Safe compiler for EQ-Proof's deliberately small linear expression language."""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass

from .errors import InvalidSpecification

MAX_EXPRESSION_LENGTH = 4096
MAX_AST_NODES = 2048


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
    if not (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    ):
        raise InvalidSpecification("Only finite numeric constants are allowed in equations")
    value = float(node.value)
    if not math.isfinite(value):
        raise InvalidSpecification("Only finite numeric constants are allowed in equations")
    return value


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
            return _linearize(node.right, variables).scaled(_number(node.left))
        except InvalidSpecification:
            return _linearize(node.left, variables).scaled(_number(node.right))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        divisor = _number(node.right)
        if divisor == 0:
            raise InvalidSpecification("Division by zero in equation")
        return _linearize(node.left, variables).scaled(1.0 / divisor)
    raise InvalidSpecification(
        "Unsupported expression. Use declared variables, finite numbers, +, -, scalar *, scalar /, and parentheses"
    )


def compile_equation(
    expression: str,
    variable_names: tuple[str, ...],
) -> tuple[tuple[float, ...], str, float]:
    """Compile ``a + 2*b <= 4`` into normalized coefficients and a right-hand side."""
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise InvalidSpecification(
            f"Equation exceeds the {MAX_EXPRESSION_LENGTH}-character limit"
        )
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise InvalidSpecification(f"Invalid equation syntax: {expression}") from exc
    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise InvalidSpecification(f"Equation exceeds the {MAX_AST_NODES}-node syntax limit")
    if not (
        isinstance(tree.body, ast.Compare)
        and len(tree.body.ops) == 1
        and len(tree.body.comparators) == 1
    ):
        raise InvalidSpecification("Each equation must contain exactly one comparison")

    operator = tree.body.ops[0]
    if not isinstance(operator, (ast.Eq, ast.LtE, ast.GtE)):
        raise InvalidSpecification("Only ==, <=, and >= relations are supported")

    variables = set(variable_names)
    left = _linearize(tree.body.left, variables)
    right = _linearize(tree.body.comparators[0], variables)
    normalized = left.add(right, -1.0)
    rhs = -normalized.constant
    coefficients = tuple(normalized.coefficients.get(name, 0.0) for name in variable_names)

    if all(abs(value) < 1e-15 for value in coefficients):
        relation_true = (
            abs(rhs) <= 1e-15
            if isinstance(operator, ast.Eq)
            else (0.0 <= rhs if isinstance(operator, ast.LtE) else 0.0 >= rhs)
        )
        if not relation_true:
            raise InvalidSpecification(f"Equation is contradictory: {expression}")
        raise InvalidSpecification(f"Equation has no variables and adds no constraint: {expression}")

    if isinstance(operator, ast.Eq):
        return coefficients, "==", rhs
    if isinstance(operator, ast.GtE):
        return tuple(-value for value in coefficients), "<=", -rhs
    return coefficients, "<=", rhs
