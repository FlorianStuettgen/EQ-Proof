# ---- test_compiler.py ----
import pytest

from eq_proof.core import compile_equation
from eq_proof.core import InvalidSpecification


def test_compiles_linear_equation_in_variable_order():
    coefficients, relation, rhs = compile_equation("a + 2*b - c/2 == 7", ("a", "b", "c"))
    assert coefficients == pytest.approx((1.0, 2.0, -0.5))
    assert relation == "=="
    assert rhs == pytest.approx(7.0)


def test_normalizes_greater_than_or_equal_to_halfspace():
    coefficients, relation, rhs = compile_equation("a >= 3", ("a",))
    assert coefficients == pytest.approx((-1.0,))
    assert relation == "<="
    assert rhs == pytest.approx(-3.0)


@pytest.mark.parametrize(
    "expression",
    [
        "a * b == 1",
        "a ** 2 == 1",
        "__import__('os').system('echo unsafe') == 0",
        "a < 1",
        "a == b == 1",
    ],
)
def test_rejects_nonlinear_unsafe_or_unsupported_syntax(expression):
    with pytest.raises(InvalidSpecification):
        compile_equation(expression, ("a", "b"))


def test_supports_parentheses_unary_and_scalar_on_right():
    coefficients, relation, rhs = compile_equation("+(a - b) * 2 <= 4", ("a", "b"))
    assert coefficients == pytest.approx((2.0, -2.0))
    assert relation == "<="
    assert rhs == pytest.approx(4.0)


@pytest.mark.parametrize("expression", ["a / 0 == 1", "unknown == 1", "1 == 2", "1 == 1", "a + == 1"])
def test_rejects_additional_invalid_equations(expression):
    with pytest.raises(InvalidSpecification):
        compile_equation(expression, ("a",))


# ---- test_engine.py ----
import json
from pathlib import Path

import pytest

from eq_proof.core import repair
from eq_proof.core import InfeasibleProblem, InvalidSpecification
from eq_proof.core import parse_specification

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
    assert result.repaired == pytest.approx({"forecast_a": 0.50, "forecast_b": 0.30, "forecast_c": 0.20}, abs=1e-9)
    assert result.repaired["forecast_c"] == 0.20
    assert result.movement_l2 == pytest.approx(2 ** 0.5 * 0.05, abs=1e-9)
    assert result.max_violation_before == pytest.approx(0.10)
    assert result.max_violation_after <= 1e-9


def test_budget_cap_and_order_are_satisfied():
    spec, values = load_example("budget_guardrail")
    result = repair(spec, values)
    assert sum(result.repaired.values()) <= 1_000_000 + 1e-5
    assert result.repaired["electrical"] <= result.repaired["mechanical"] + 1e-5
    assert min(result.repaired.values()) >= 0


def test_feasible_input_is_not_moved():
    spec = parse_specification({
        "schema_version": "1.0",
        "name": "simple",
        "variables": {"x": {"lower": 0, "upper": 1}},
        "equations": [],
    })
    result = repair(spec, {"x": 0.4})
    assert result.status == "already_feasible"
    assert result.movement_l2 == 0
    assert result.iterations == 0


def test_fixed_value_outside_bounds_is_infeasible():
    spec = parse_specification({
        "schema_version": "1.0",
        "name": "fixed",
        "variables": {"x": {"lower": 0, "upper": 1, "fixed": True}},
        "equations": [{"id": "target", "expression": "x == 0.5"}],
    })
    with pytest.raises(InfeasibleProblem):
        repair(spec, {"x": 2.0})


def test_input_shape_is_exact():
    spec = parse_specification({
        "schema_version": "1.0",
        "name": "shape",
        "variables": {"x": {}},
        "equations": [],
    })
    with pytest.raises(InvalidSpecification, match="unknown variables"):
        repair(spec, {"x": 1, "y": 2})


@pytest.mark.parametrize("values", [{}, {"x": "bad"}, {"x": float("nan")}])
def test_rejects_missing_or_nonfinite_inputs(values):
    spec = parse_specification({
        "schema_version": "1.0",
        "name": "input-validation",
        "variables": {"x": {}},
        "equations": [],
    })
    with pytest.raises(InvalidSpecification):
        repair(spec, values)


def test_nonconvergent_problem_is_reported():
    spec = parse_specification({
        "schema_version": "1.0",
        "name": "empty-intersection",
        "variables": {"x": {}},
        "equations": [
            {"id": "low", "expression": "x >= 1"},
            {"id": "high", "expression": "x <= 0"},
        ],
    })
    with pytest.raises(InfeasibleProblem):
        repair(spec, {"x": 0.5}, max_iterations=20)


# ---- test_solver.py ----
import numpy as np
import pytest

from eq_proof.core import project
from eq_proof.core import parse_specification


def spec():
    return parse_specification({
        "schema_version": "1.0",
        "name": "solver",
        "variables": {"x": {}},
        "equations": [{"id": "cap", "expression": "x <= 1"}],
    })


def test_solver_argument_validation():
    with pytest.raises(ValueError, match="tolerance"):
        project(spec(), np.array([2.0]), tolerance=0)
    with pytest.raises(ValueError, match="max_iterations"):
        project(spec(), np.array([2.0]), max_iterations=0)


def test_all_fixed_feasible_problem_returns_exact_submission():
    fixed_spec = parse_specification({
        "schema_version": "1.0",
        "name": "all-fixed",
        "variables": {"x": {"lower": 0, "upper": 1, "fixed": True}},
        "equations": [{"id": "same", "expression": "x == 0.5"}],
    })
    result, iterations = project(fixed_spec, np.array([0.5]))
    assert iterations == 0
    assert result.tolist() == [0.5]


@pytest.mark.parametrize(
    "rule, submitted, message",
    [
        ({"lower": 0, "fixed": True}, -1.0, "lower bound"),
        ({"upper": 1, "fixed": True}, 2.0, "upper bound"),
    ],
)
def test_fixed_bound_violations_fail(rule, submitted, message):
    fixed_spec = parse_specification({
        "schema_version": "1.0",
        "name": "fixed-bound",
        "variables": {"x": rule},
        "equations": [],
    })
    from eq_proof.core import InfeasibleProblem
    with pytest.raises(InfeasibleProblem, match=message):
        project(fixed_spec, np.array([submitted]))


def test_fixed_values_can_make_equation_infeasible():
    fixed_spec = parse_specification({
        "schema_version": "1.0",
        "name": "fixed-equation",
        "variables": {"x": {"fixed": True}},
        "equations": [{"id": "target", "expression": "x == 1"}],
    })
    from eq_proof.core import InfeasibleProblem
    with pytest.raises(InfeasibleProblem, match="Fixed values"):
        project(fixed_spec, np.array([0.0]))


# ---- test_validation.py ----
import json
import math

import pytest

from eq_proof.core import InvalidSpecification
from eq_proof.core import load_specification, parse_specification

BASE = {
    "schema_version": "1.0",
    "name": "valid",
    "variables": {"x": {}},
    "equations": [],
}


def changed(**updates):
    value = json.loads(json.dumps(BASE))
    value.update(updates)
    return value


@pytest.mark.parametrize(
    "document, message",
    [
        ([], "root"),
        (changed(schema_version="2.0"), "Unsupported"),
        (changed(name=""), "name"),
        (changed(description=3), "description"),
        (changed(variables={}), "variables"),
        (changed(variables={"not valid": {}}), "variable name"),
        (changed(variables={"x": []}), "rule"),
        (changed(variables={"x": {"lower": True}}), "finite number"),
        (changed(variables={"x": {"lower": math.inf}}), "finite"),
        (changed(variables={"x": {"lower": 2, "upper": 1}}), "exceeds"),
        (changed(variables={"x": {"fixed": "yes"}}), "boolean"),
        (changed(equations={}), "array"),
        (changed(equations=["x == 1"]), "object"),
        (changed(equations=[{"id": "", "expression": "x == 1"}]), "id"),
        (changed(equations=[{"id": "a", "expression": ""}]), "non-empty expression"),
        (changed(equations=[{"id": "a", "expression": "x == 1"}, {"id": "a", "expression": "x == 2"}]), "Duplicate"),
    ],
)
def test_rejects_invalid_specifications(document, message):
    with pytest.raises(InvalidSpecification, match=message):
        parse_specification(document)


def test_load_specification_wraps_bad_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{")
    with pytest.raises(InvalidSpecification, match="Unable to read"):
        load_specification(path)
