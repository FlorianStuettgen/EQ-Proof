import pytest

from eq_proof import InvalidSpecification, compile_equation


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


def test_supports_parentheses_unary_and_scalar_on_right():
    coefficients, relation, rhs = compile_equation("+(a - b) * 2 <= 4", ("a", "b"))
    assert coefficients == pytest.approx((2.0, -2.0))
    assert relation == "<="
    assert rhs == pytest.approx(4.0)


@pytest.mark.parametrize(
    "expression",
    [
        "a * b == 1",
        "a ** 2 == 1",
        "__import__('os').system('echo unsafe') == 0",
        "a < 1",
        "a == b == 1",
        "a / 0 == 1",
        "unknown == 1",
        "1 == 2",
        "1 == 1",
        "a + == 1",
        "1e309 * a == 1",
    ],
)
def test_rejects_nonlinear_unsafe_or_invalid_syntax(expression):
    with pytest.raises(InvalidSpecification):
        compile_equation(expression, ("a", "b"))


def test_rejects_excessive_expression_size():
    with pytest.raises(InvalidSpecification, match="character limit"):
        compile_equation("a" * 5000 + " == 1", ("a",))
