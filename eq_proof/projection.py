from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

import numpy as np
import sympy as sp

from .linear import NonlinearConstraint, linear_coefficients
from .spec import Spec


@dataclass(frozen=True)
class ConvexSet:
    kind: str
    coeffs: np.ndarray
    rhs: float
    label: str


@dataclass
class ProjectionResult:
    values: Dict[str, float]
    delta_l2: float
    iterations: int
    converged: bool
    max_residual: float
    residuals: List[Dict[str, Any]]
    unsupported: List[str]


def _array_from_coeffs(coeffs: Dict[str, float], variables: Sequence[str]) -> np.ndarray:
    return np.array([float(coeffs.get(v, 0.0)) for v in variables], dtype=float)


def _project_onto_set(x: np.ndarray, cset: ConvexSet) -> np.ndarray:
    a = cset.coeffs
    norm2 = float(a @ a)
    if norm2 <= 0.0:
        return x
    residual = float(a @ x - cset.rhs)
    if cset.kind == "eq":
        return x - (residual / norm2) * a
    if cset.kind == "leq" and residual > 0.0:
        return x - (residual / norm2) * a
    return x


def _set_residual(x: np.ndarray, cset: ConvexSet) -> float:
    residual = float(cset.coeffs @ x - cset.rhs)
    if cset.kind == "eq":
        return abs(residual)
    return max(0.0, residual)


def dykstra_project(
    x0: Sequence[float],
    sets: Sequence[ConvexSet],
    *,
    max_iter: int = 10000,
    tol: float = 1e-10,
) -> Tuple[np.ndarray, int, bool]:
    """Project x0 onto an intersection of affine hyperplanes and halfspaces."""
    x = np.array(x0, dtype=float)
    if not sets:
        return x, 0, True

    corrections = [np.zeros_like(x) for _ in sets]
    converged = False
    for iteration in range(1, max_iter + 1):
        previous = x.copy()
        for idx, cset in enumerate(sets):
            y = x + corrections[idx]
            projected = _project_onto_set(y, cset)
            corrections[idx] = y - projected
            x = projected
        if float(np.linalg.norm(x - previous)) <= tol:
            converged = True
            return x, iteration, converged
    return x, max_iter, converged


def _equality_to_linear(expr_str: str, variables: Sequence[str]) -> Tuple[Dict[str, float], float]:
    syms = {name: sp.symbols(name, real=True) for name in variables}
    expr = sp.sympify(expr_str, locals={"Eq": sp.Eq, **syms})
    if not isinstance(expr, sp.Equality):
        raise NonlinearConstraint("Equality constraint must use Eq(lhs, rhs)")
    coeffs, const = linear_coefficients(expr.lhs - expr.rhs, variables)
    return coeffs, -const


def _linear_constraint_from_spec(c: Dict[str, Any], variables: Sequence[str]) -> Tuple[Dict[str, float], float, str]:
    if c["type"] == "linear_eq":
        return dict(c["coeffs"]), float(c["rhs"]), "eq"
    if c["type"] == "linear_leq":
        return dict(c["coeffs"]), float(c["rhs"]), "leq"
    if c["type"] == "equality":
        coeffs, rhs = _equality_to_linear(c["expr"], variables)
        return coeffs, rhs, "eq"
    raise ValueError(f"Unsupported linear constraint type {c.get('type')!r}")


def build_convex_sets(spec: Spec, values: Dict[str, float]) -> Tuple[List[ConvexSet], List[str]]:
    variables = list(spec.variables)
    sets: List[ConvexSet] = []
    unsupported: List[str] = []

    for name in getattr(spec, "fixed", []):
        if name in variables and name in values:
            sets.append(
                ConvexSet(
                    "eq",
                    _array_from_coeffs({name: 1.0}, variables),
                    float(values[name]),
                    f"fixed:{name}",
                )
            )

    for c in spec.constraints:
        ctype = c.get("type")
        try:
            if ctype == "bounds":
                var = c["var"]
                lower = c.get("lower")
                upper = c.get("upper")
                if lower is not None:
                    sets.append(
                        ConvexSet(
                            "leq",
                            _array_from_coeffs({var: -1.0}, variables),
                            -float(lower),
                            f"{var} >= {lower}",
                        )
                    )
                if upper is not None:
                    sets.append(
                        ConvexSet(
                            "leq",
                            _array_from_coeffs({var: 1.0}, variables),
                            float(upper),
                            f"{var} <= {upper}",
                        )
                    )
            elif ctype in ("linear_eq", "linear_leq", "equality"):
                coeffs, rhs, kind = _linear_constraint_from_spec(c, variables)
                sets.append(ConvexSet(kind, _array_from_coeffs(coeffs, variables), rhs, c.get("expr", ctype)))
            elif ctype == "sum_leq":
                coeffs = {var: 1.0 for var in c["vars"]}
                if "cap_var" in c:
                    cap_var = c["cap_var"]
                    if cap_var not in variables and cap_var not in values:
                        raise ValueError(f"Unknown cap_var {cap_var!r}")
                    if cap_var in variables:
                        coeffs[cap_var] = coeffs.get(cap_var, 0.0) - 1.0
                        rhs = 0.0
                    else:
                        rhs = float(values[cap_var])
                else:
                    rhs = float(c["cap"])
                sets.append(
                    ConvexSet(
                        "leq",
                        _array_from_coeffs(coeffs, variables),
                        rhs,
                        " + ".join(c["vars"]) + " <= " + str(c.get("cap_var", c.get("cap"))),
                    )
                )
            elif ctype == "simplex":
                coeffs = {var: 1.0 for var in c["vars"]}
                sets.append(ConvexSet("eq", _array_from_coeffs(coeffs, variables), 1.0, "simplex sum"))
                for var in c["vars"]:
                    sets.append(ConvexSet("leq", _array_from_coeffs({var: -1.0}, variables), 0.0, f"{var} >= 0"))
            elif ctype == "monotone":
                vars_ = c["vars"]
                for left, right in zip(vars_, vars_[1:]):
                    sets.append(
                        ConvexSet(
                            "leq",
                            _array_from_coeffs({left: 1.0, right: -1.0}, variables),
                            0.0,
                            f"{left} <= {right}",
                        )
                    )
            else:
                unsupported.append(str(ctype))
        except (NonlinearConstraint, KeyError, TypeError, ValueError) as exc:
            unsupported.append(f"{ctype}: {exc}")

    return sets, unsupported


def project_spec(
    spec: Spec,
    values: Dict[str, float],
    *,
    max_iter: int = 10000,
    tol: float = 1e-10,
) -> ProjectionResult:
    variables = list(spec.variables)
    x0 = []
    unsupported: List[str] = []
    for var in variables:
        try:
            value = float(values.get(var, 0.0))
            if not math.isfinite(value):
                raise ValueError("not finite")
            x0.append(value)
        except Exception as exc:
            unsupported.append(f"{var}: {exc}")

    sets, set_unsupported = build_convex_sets(spec, values)
    unsupported.extend(set_unsupported)
    if unsupported:
        return ProjectionResult(dict(values), 0.0, 0, False, math.inf, [], unsupported)

    projected, iterations, converged = dykstra_project(x0, sets, max_iter=max_iter, tol=tol)
    for fixed_var in getattr(spec, "fixed", []):
        if fixed_var in variables and fixed_var in values:
            projected[variables.index(fixed_var)] = float(values[fixed_var])
    repaired = dict(values)
    for var, value in zip(variables, projected):
        repaired[var] = float(value)

    residuals = [
        {"constraint": cset.label, "type": cset.kind, "residual": _set_residual(projected, cset)}
        for cset in sets
    ]
    max_residual = max((float(item["residual"]) for item in residuals), default=0.0)
    delta_l2 = float(np.linalg.norm(projected - np.array(x0, dtype=float)))
    return ProjectionResult(repaired, delta_l2, iterations, converged, max_residual, residuals, [])
