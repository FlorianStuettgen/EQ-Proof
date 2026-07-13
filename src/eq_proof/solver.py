"""Euclidean projection and repair orchestration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import math

import numpy as np

from .model import (
    ConstraintCheck, InfeasibleProblem, InvalidSpecification, RepairResult,
    Specification, checks, max_violation,
)


Projector = Callable[[np.ndarray], np.ndarray]


def _box_projector(lower: np.ndarray, upper: np.ndarray) -> Projector:
    def project(vector: np.ndarray) -> np.ndarray:
        return np.minimum(np.maximum(vector, lower), upper)
    return project


def _hyperplane_projector(coefficients: np.ndarray, rhs: float) -> Projector:
    denominator = float(np.dot(coefficients, coefficients))

    def project(vector: np.ndarray) -> np.ndarray:
        return vector - ((float(np.dot(coefficients, vector)) - rhs) / denominator) * coefficients
    return project


def _halfspace_projector(coefficients: np.ndarray, rhs: float) -> Projector:
    denominator = float(np.dot(coefficients, coefficients))

    def project(vector: np.ndarray) -> np.ndarray:
        excess = float(np.dot(coefficients, vector)) - rhs
        return vector if excess <= 0.0 else vector - (excess / denominator) * coefficients
    return project


def build_projectors(
    specification: Specification,
    submitted: np.ndarray,
    *,
    tolerance: float,
) -> tuple[np.ndarray, list[Projector]]:
    """Build projectors in free-variable space so fixed values remain exact."""
    free_indices = np.asarray(
        [index for index, variable in enumerate(specification.variables) if not variable.fixed],
        dtype=int,
    )
    fixed_indices = np.asarray(
        [index for index, variable in enumerate(specification.variables) if variable.fixed],
        dtype=int,
    )

    for index in fixed_indices:
        variable = specification.variables[int(index)]
        fixed_value = float(submitted[index])
        if variable.lower is not None and fixed_value < variable.lower - tolerance:
            raise InfeasibleProblem(f"Fixed variable {variable.name}={fixed_value} violates its lower bound")
        if variable.upper is not None and fixed_value > variable.upper + tolerance:
            raise InfeasibleProblem(f"Fixed variable {variable.name}={fixed_value} violates its upper bound")

    if free_indices.size:
        lower = np.asarray([
            specification.variables[int(index)].lower
            if specification.variables[int(index)].lower is not None else -np.inf
            for index in free_indices
        ], dtype=float)
        upper = np.asarray([
            specification.variables[int(index)].upper
            if specification.variables[int(index)].upper is not None else np.inf
            for index in free_indices
        ], dtype=float)
        projectors: list[Projector] = [_box_projector(lower, upper)]
    else:
        projectors = []

    for constraint in specification.constraints:
        full_coefficients = np.asarray(constraint.coefficients, dtype=float)
        coefficients = full_coefficients[free_indices]
        fixed_contribution = (
            float(np.dot(full_coefficients[fixed_indices], submitted[fixed_indices]))
            if fixed_indices.size else 0.0
        )
        rhs = constraint.rhs - fixed_contribution
        denominator = float(np.dot(coefficients, coefficients))
        if denominator <= 1e-30:
            violation = abs(rhs) if constraint.relation == "==" else max(0.0, -rhs)
            if violation > tolerance:
                raise InfeasibleProblem(
                    f"Fixed values make constraint {constraint.identifier!r} infeasible"
                )
            continue
        if constraint.relation == "==":
            projectors.append(_hyperplane_projector(coefficients, rhs))
        else:
            projectors.append(_halfspace_projector(coefficients, rhs))
    return free_indices, projectors


def project(
    specification: Specification,
    submitted: np.ndarray,
    *,
    tolerance: float = 1e-10,
    max_iterations: int = 20_000,
) -> tuple[np.ndarray, int]:
    """Run Dykstra's algorithm, which converges to the Euclidean projection."""
    if tolerance <= 0:
        raise ValueError("tolerance must be positive")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")

    free_indices, projectors = build_projectors(specification, submitted, tolerance=tolerance)
    if not projectors:
        return submitted.astype(float, copy=True), 0

    corrections = [np.zeros(free_indices.size, dtype=float) for _ in projectors]
    current = submitted[free_indices].astype(float, copy=True)

    for iteration in range(1, max_iterations + 1):
        previous = current.copy()
        for index, projector in enumerate(projectors):
            shifted = current + corrections[index]
            projected = projector(shifted)
            corrections[index] = shifted - projected
            current = projected
        if float(np.linalg.norm(current - previous, ord=np.inf)) <= tolerance:
            result = submitted.astype(float, copy=True)
            result[free_indices] = current
            return result, iteration

    raise InfeasibleProblem(
        f"Projection did not converge within {max_iterations} iterations; the feasible set may be empty"
    )


def _input_vector(specification: Specification, values: Mapping[str, object]) -> np.ndarray:
    expected = set(specification.variable_names)
    actual = set(values)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        parts = []
        if missing:
            parts.append(f"missing variables: {', '.join(missing)}")
        if extra:
            parts.append(f"unknown variables: {', '.join(extra)}")
        raise InvalidSpecification("Input variables do not match the specification (" + "; ".join(parts) + ")")

    numeric: list[float] = []
    for name in specification.variable_names:
        value = values[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise InvalidSpecification(f"Input value for {name} must be a finite number")
        number = float(value)
        if not math.isfinite(number):
            raise InvalidSpecification(f"Input value for {name} must be finite")
        numeric.append(number)
    return np.asarray(numeric, dtype=float)


def repair(
    specification: Specification,
    values: Mapping[str, object],
    *,
    tolerance: float = 1e-10,
    max_iterations: int = 20_000,
) -> RepairResult:
    submitted_vector = _input_vector(specification, values)
    before = checks(specification, submitted_vector, tolerance)
    before_max = max_violation(before)

    if before_max <= tolerance:
        repaired_vector = submitted_vector.copy()
        iterations = 0
        status = "already_feasible"
    else:
        repaired_vector, iterations = project(
            specification,
            submitted_vector,
            tolerance=tolerance,
            max_iterations=max_iterations,
        )
        status = "repaired"

    after = checks(specification, repaired_vector, tolerance * 10)
    after_max = max_violation(after)
    if after_max > tolerance * 10:
        raise InfeasibleProblem(
            f"Projection stopped without a feasible result; maximum residual is {after_max:.3e}"
        )

    submitted = {name: float(submitted_vector[index]) for index, name in enumerate(specification.variable_names)}
    repaired = {name: float(repaired_vector[index]) for index, name in enumerate(specification.variable_names)}
    movement = float(np.linalg.norm(repaired_vector - submitted_vector, ord=2))
    return RepairResult(
        status=status,
        submitted=submitted,
        repaired=repaired,
        movement_l2=movement,
        iterations=iterations,
        tolerance=tolerance,
        max_violation_before=before_max,
        max_violation_after=after_max,
        checks_before=before,
        checks_after=after,
    )
