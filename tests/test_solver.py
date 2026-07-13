import json
from pathlib import Path

import numpy as np
import pytest

from eq_proof import InfeasibleProblem, InvalidSpecification, parse_specification, repair
from eq_proof.solver import project

ROOT = Path(__file__).resolve().parents[1]


def load_example(name):
    directory = ROOT / "examples" / name
    spec = parse_specification(json.loads((directory / "spec.json").read_text()))
    values = json.loads((directory / "input.json").read_text())
    return spec, values


def test_allocation_example_is_minimal_and_preserves_fixed_value():
    spec, values = load_example("portfolio_allocation")
    result = repair(spec, values)
    assert result.status == "repaired"
    assert result.repaired == pytest.approx(
        {"forecast_a": 0.50, "forecast_b": 0.30, "forecast_c": 0.20}, abs=1e-9
    )
    assert result.repaired["forecast_c"] == 0.20
    assert result.movement_l2 == pytest.approx(2**0.5 * 0.05, abs=1e-9)
    assert result.objective_value == pytest.approx(0.0025)
    assert result.max_violation_before == pytest.approx(0.10)
    assert result.max_violation_after <= 1e-9


def test_budget_cap_and_order_are_satisfied():
    spec, values = load_example("budget_guardrail")
    result = repair(spec, values)
    assert sum(result.repaired.values()) <= 1_000_000 + 1e-5
    assert result.repaired["electrical"] <= result.repaired["mechanical"] + 1e-5
    assert min(result.repaired.values()) >= 0


def test_capacity_plan_respects_fixed_and_monotonic_constraints():
    spec, values = load_example("capacity_plan")
    result = repair(spec, values)
    repaired = result.repaired
    assert repaired["q1"] == 100
    assert repaired["q1"] <= repaired["q2"] <= repaired["q3"] <= repaired["q4"]
    assert sum(repaired.values()) <= 520 + 1e-7


def test_feasible_input_is_not_moved():
    spec = parse_specification(
        {
            "schema_version": "1.0",
            "name": "simple",
            "variables": {"x": {"lower": 0, "upper": 1}},
            "equations": [],
        }
    )
    result = repair(spec, {"x": 0.4})
    assert result.status == "already_feasible"
    assert result.movement_l2 == 0
    assert result.iterations == 0


def test_fixed_value_outside_bounds_is_infeasible():
    spec = parse_specification(
        {
            "schema_version": "1.0",
            "name": "fixed",
            "variables": {"x": {"lower": 0, "upper": 1, "fixed": True}},
            "equations": [{"id": "target", "expression": "x == 0.5"}],
        }
    )
    with pytest.raises(InfeasibleProblem):
        repair(spec, {"x": 2.0})


def test_input_shape_is_exact():
    spec = parse_specification(
        {
            "schema_version": "1.0",
            "name": "shape",
            "variables": {"x": {}},
            "equations": [],
        }
    )
    with pytest.raises(InvalidSpecification, match="unknown variables"):
        repair(spec, {"x": 1, "y": 2})


@pytest.mark.parametrize("values", [{}, {"x": "bad"}, {"x": float("nan")}, []])
def test_rejects_missing_or_nonfinite_inputs(values):
    spec = parse_specification(
        {
            "schema_version": "1.0",
            "name": "input-validation",
            "variables": {"x": {}},
            "equations": [],
        }
    )
    with pytest.raises(InvalidSpecification):
        repair(spec, values)


def test_nonconvergent_problem_is_reported():
    spec = parse_specification(
        {
            "schema_version": "1.0",
            "name": "empty-intersection",
            "variables": {"x": {}},
            "equations": [
                {"id": "low", "expression": "x >= 1"},
                {"id": "high", "expression": "x <= 0"},
            ],
        }
    )
    with pytest.raises(InfeasibleProblem):
        repair(spec, {"x": 0.5}, max_iterations=20)


def test_solver_argument_and_vector_validation():
    spec = parse_specification({
        "schema_version": "1.0",
        "name": "solver",
        "variables": {"x": {}},
        "equations": [{"id": "cap", "expression": "x <= 1"}],
    })
    with pytest.raises(ValueError, match="tolerance"):
        project(spec, np.array([2.0]), tolerance=0)
    with pytest.raises(ValueError, match="max_iterations"):
        project(spec, np.array([2.0]), max_iterations=0)
    with pytest.raises(InvalidSpecification, match="one-dimensional"):
        project(spec, np.array([[2.0]]))
    with pytest.raises(InvalidSpecification, match="finite"):
        project(spec, np.array([np.inf]))


def test_all_fixed_feasible_problem_and_fixed_upper_violation():
    feasible = parse_specification(
        {
            "schema_version": "1.0",
            "name": "all-fixed",
            "variables": {"x": {"lower": 0, "upper": 1, "fixed": True}},
            "equations": [{"id": "same", "expression": "x == 0.5"}],
        }
    )
    result, iterations = project(feasible, np.array([0.5]))
    assert iterations == 0
    assert result.tolist() == [0.5]

    with pytest.raises(InfeasibleProblem, match="upper bound"):
        project(feasible, np.array([2.0]))


def test_fixed_values_can_make_inequality_infeasible_or_redundant():
    infeasible = parse_specification(
        {
            "schema_version": "1.0",
            "name": "fixed-inequality",
            "variables": {"x": {"fixed": True}},
            "equations": [{"id": "cap", "expression": "x <= 1"}],
        }
    )
    with pytest.raises(InfeasibleProblem, match="Fixed values"):
        project(infeasible, np.array([2.0]))
    result, iterations = project(infeasible, np.array([0.5]))
    assert iterations == 0
    assert result.tolist() == [0.5]
