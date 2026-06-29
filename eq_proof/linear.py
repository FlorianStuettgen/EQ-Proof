from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

import sympy as sp


class NonlinearConstraint(ValueError):
    """Raised when an expression cannot be represented as a linear form."""


RELATION_RE = re.compile(r"(?<![<>=!])(?:<=|>=|==|=)(?![<>=])")


@dataclass(frozen=True)
class LinearRelation:
    op: str
    coeffs: Dict[str, float]
    rhs: float
    source: str


def symbol_names_from_text(text: str) -> List[str]:
    names = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", text))
    names.difference_update({"Eq", "and", "or", "simplex", "sum_leq", "monotone", "fixed", "constant"})
    return sorted(names)


def sympy_context(names: Iterable[str]) -> Dict[str, sp.Symbol]:
    return {name: sp.symbols(name, real=True) for name in sorted(set(names))}


def parse_expression(text: str, names: Iterable[str] | None = None) -> sp.Expr:
    all_names = set(names or []) | set(symbol_names_from_text(text))
    return sp.sympify(text.strip(), locals=sympy_context(all_names))


def split_relation(text: str) -> Tuple[str, str, str]:
    matches = list(RELATION_RE.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"Expected one relation operator in {text!r}")
    match = matches[0]
    op = match.group(0)
    if op == "==":
        op = "="
    return text[: match.start()].strip(), op, text[match.end() :].strip()


def linear_coefficients(expr: sp.Expr, variables: Sequence[str]) -> Tuple[Dict[str, float], float]:
    symbols = sympy_context(variables)
    zero_subs = {sym: 0 for sym in symbols.values()}
    expanded = sp.expand(expr)
    coeffs: Dict[str, float] = {}
    rebuilt = expanded.subs(zero_subs)

    for name in variables:
        sym = symbols[name]
        coeff = sp.diff(expanded, sym)
        if coeff.free_symbols:
            raise NonlinearConstraint(f"Expression is nonlinear in {name}")
        coeff_f = float(sp.N(coeff))
        if abs(coeff_f) > 0.0:
            coeffs[name] = coeff_f
        rebuilt += coeff * sym

    residual = sp.simplify(expanded - rebuilt)
    if residual != 0:
        raise NonlinearConstraint("Expression contains nonlinear or unsupported terms")

    const = float(sp.N(expanded.subs(zero_subs)))
    return coeffs, const


def compile_linear_relation(text: str, variables: Sequence[str] | None = None) -> LinearRelation:
    lhs, op, rhs = split_relation(text)
    names = sorted(set(variables or []) | set(symbol_names_from_text(lhs)) | set(symbol_names_from_text(rhs)))
    lhs_expr = parse_expression(lhs, names)
    rhs_expr = parse_expression(rhs, names)
    coeffs, const = linear_coefficients(lhs_expr - rhs_expr, names)

    if op == "=":
        return LinearRelation("=", coeffs, -const, text)
    if op == "<=":
        return LinearRelation("<=", coeffs, -const, text)
    if op == ">=":
        return LinearRelation("<=", {k: -v for k, v in coeffs.items()}, const, text)
    raise ValueError(f"Unsupported relation operator {op!r}")


def is_simple_number(text: str) -> bool:
    try:
        float(parse_expression(text, []))
        return True
    except Exception:
        return False


def as_float(text: str) -> float:
    value = parse_expression(text, [])
    if value.free_symbols:
        raise ValueError(f"Expected a numeric value, got {text!r}")
    return float(sp.N(value))
