"""Constraint diagnostics before and after projection."""

from __future__ import annotations

import numpy as np

from .domain import ConstraintCheck, Specification


def checks(
    specification: Specification,
    vector: np.ndarray,
    tolerance: float,
) -> tuple[ConstraintCheck, ...]:
    output: list[ConstraintCheck] = []
    for index, variable in enumerate(specification.variables):
        value = float(vector[index])
        if variable.lower is not None:
            violation = max(0.0, variable.lower - value)
            output.append(
                ConstraintCheck(
                    f"bound:{variable.name}:lower",
                    f"{variable.name} >= {variable.lower}",
                    ">=",
                    value,
                    variable.lower,
                    violation,
                    violation <= tolerance,
                )
            )
        if variable.upper is not None:
            violation = max(0.0, value - variable.upper)
            output.append(
                ConstraintCheck(
                    f"bound:{variable.name}:upper",
                    f"{variable.name} <= {variable.upper}",
                    "<=",
                    value,
                    variable.upper,
                    violation,
                    violation <= tolerance,
                )
            )

    for constraint in specification.constraints:
        lhs = float(np.dot(np.asarray(constraint.coefficients, dtype=float), vector))
        violation = (
            abs(lhs - constraint.rhs)
            if constraint.relation == "=="
            else max(0.0, lhs - constraint.rhs)
        )
        output.append(
            ConstraintCheck(
                constraint.identifier,
                constraint.source,
                constraint.relation,
                lhs,
                constraint.rhs,
                violation,
                violation <= tolerance,
            )
        )
    return tuple(output)


def max_violation(items: tuple[ConstraintCheck, ...]) -> float:
    return max((item.violation for item in items), default=0.0)


def check_to_dict(item: ConstraintCheck) -> dict[str, object]:
    return {
        "id": item.identifier,
        "source": item.source,
        "relation": item.relation,
        "lhs": item.lhs,
        "rhs": item.rhs,
        "violation": item.violation,
        "satisfied": item.satisfied,
    }
