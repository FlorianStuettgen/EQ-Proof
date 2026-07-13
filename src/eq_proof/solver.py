"""Euclidean projection and repair orchestration."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping

import numpy as np

from .diagnostics import checks, max_violation
from .domain import RepairResult, Specification
from .errors import InfeasibleProblem, InvalidSpecification

Projector = Callable[[np.ndarray], np.ndarray]
DEFAULT_TOLERANCE = 1e-10
DEFAULT_MAX_ITERATIONS = 20_000


def _box_projector(lower: np.ndarray, upper: np.ndarray) -> Projector:
    def project(vector: np.ndarray) -> np.ndarray:
        return np.minimum(np.maximum(vector, lower), upper)

    return project


def _hyperplane_projector(coefficients: np.ndarray, rhs: float) -> Projector:
    denominator = float(np.dot(coefficients, coefficients))

    def project(vector: np.ndarray) -> np.ndarray:
        return vector - (
            (float(np.dot(coefficients, vector)) - rhs) / denominator
        ) * coefficients

    return project


def _halfspace_projector(coefficients: np.ndarray, rhs: float) -> Projector:
    denominator = float(np.dot(coefficients, coefficients))

    def project(vector: np.ndarray) -> np.ndarray:
        excess = float(np.dot(coefficients, vector)) - rhs
        return vector if excess <= 0.0 else vector - (excess / denominator) * coefficients

    return project


def _validate_vector(specification: Specification, submitted: np.ndarray) -> np.ndarray:
    vector = np.asarray(submitted, dtype=float)
    if vector.ndim != 1 or vector.shape[0] != len(specification.variables):
        raise InvalidSpecification(
            f"Expected a one-dimensional vector with {len(specification.variables)} values"
        )
    if not np.all(np.isfinite(vector)):
        raise InvalidSpecification("Submitted vector must contain only finite values")
    return vector


def build_projectors(
    specification: Specification,
    submitted: np.ndarray,
    *,
    tolerance: float,
) -> tuple[np.ndarray, list[Projector]]:
    """Build projectors in free-variable space so fixed values remain exact."""
    vector = _validate_vector(specification, submitted)
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
        fixed_value = float(vector[index])
        if variable.lower is not None and fixed_value < variable.lower - tolerance:
            raise InfeasibleProblem(
                f"Fixed variable {variable.name}={fixed_value} violates its lower bound"
            )
        if variable.upper is not None and fixed_value > variable.upper + tolerance:
            raise InfeasibleProblem(
                f"Fixed variable {variable.name}={fixed_value} violates its upper bound"
            )

    projectors: list[Projector] = []
    if free_indices.size:
        lower = np.asarray(
            [
                specification.variables[int(index)].lower
                if specification.variables[int(index)].lower is not None
                else -np.inf
                for index in free_indices
            ],
            dtype=float,
        )
        upper = np.asarray(
            [
                specification.variables[int(index)].upper
                if specification.variables[int(index)].upper is not None
                else np.inf
                for index in free_indices
            ],
            dtype=float,
        )
        projectors.append(_box_projector(lower, upper))

    for constraint in specification.constraints:
        full_coefficients = np.asarray(constraint.coefficients, dtype=float)
        coefficients = full_coefficients[free_indices]
        fixed_contribution = (
            float(np.dot(full_coefficients[fixed_indices], vector[fixed_indices]))
            if fixed_indices.size
            else 0.0
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
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> tuple[np.ndarray, int]:
    """Compute the Euclidean projection using Dykstra's algorithm."""
    if tolerance <= 0 or not math.isfinite(tolerance):
        raise ValueError("tolerance must be a positive finite number")
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")

    vector = _validate_vector(specification, submitted)
    free_indices, projectors = build_projectors(
        specification,
        vector,
        tolerance=tolerance,
    )
    if not projectors:
        return vector.astype(float, copy=True), 0

    corrections = [np.zeros(free_indices.size, dtype=float) for _ in projectors]
    current = vector[free_indices].astype(float, copy=True)

    for iteration in range(1, max_iterations + 1):
        previous = current.copy()
        for index, projector in enumerate(projectors):
            shifted = current + corrections[index]
            projected = projector(shifted)
            corrections[index] = shifted - projected
            current = projected
        if float(np.linalg.norm(current - previous, ord=np.inf)) <= tolerance:
            result = vector.astype(float, copy=True)
            result[free_indices] = current
            return result, iteration

    raise InfeasibleProblem(
        f"Projection did not converge within {max_iterations} iterations; "
        "the feasible set may be empty or numerically ill-conditioned"
    )


def input_vector(
    specification: Specification,
    values: Mapping[str, object],
) -> np.ndarray:
    if not isinstance(values, Mapping):
        raise InvalidSpecification("Input values must be a JSON object")
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
        raise InvalidSpecification(
            "Input variables do not match the specification (" + "; ".join(parts) + ")"
        )

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
    tolerance: float = DEFAULT_TOLERANCE,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
) -> RepairResult:
    submitted_vector = input_vector(specification, values)
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

    feasibility_tolerance = max(tolerance * 10.0, 1e-12)
    after = checks(specification, repaired_vector, feasibility_tolerance)
    after_max = max_violation(after)
    if after_max > feasibility_tolerance:
        raise InfeasibleProblem(
            "Projection stopped without a feasible result; "
            f"maximum residual is {after_max:.3e}"
        )

    submitted_map = {
        name: float(submitted_vector[index])
        for index, name in enumerate(specification.variable_names)
    }
    repaired_map = {
        name: float(repaired_vector[index])
        for index, name in enumerate(specification.variable_names)
    }
    movement = float(np.linalg.norm(repaired_vector - submitted_vector, ord=2))
    return RepairResult(
        status=status,
        submitted=submitted_map,
        repaired=repaired_map,
        movement_l2=movement,
        objective_value=0.5 * movement * movement,
        iterations=iterations,
        tolerance=tolerance,
        max_iterations=max_iterations,
        max_violation_before=before_max,
        max_violation_after=after_max,
        checks_before=before,
        checks_after=after,
    )
