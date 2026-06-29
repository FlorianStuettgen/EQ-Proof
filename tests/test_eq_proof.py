from eq_proof.attest import attest
from eq_proof.compiler import compile_written_constraints, spec_to_dict
from eq_proof.diagnose import diagnose_and_repair
from eq_proof.repair import project_simplex
from eq_proof.verify import verify_hmac


def assert_close(left, right, tol=1e-9):
    assert abs(left - right) <= tol


def test_simplex_projection_helper():
    projected = project_simplex([0.7, 0.4, 0.2])
    assert_close(sum(projected), 1.0)
    assert all(value >= -1e-12 for value in projected)


def test_written_constraints_project_to_minimal_simplex_change():
    spec = compile_written_constraints(
        """
        variables: p1, p2, p3
        0 <= p1 <= 1
        0 <= p2 <= 1
        0 <= p3 <= 1
        p1 + p2 + p3 = 1
        """,
        name="probability_demo",
    )

    result = diagnose_and_repair(spec, {"p1": 0.7, "p2": 0.4, "p3": 0.2})

    assert_close(result["repaired"]["p1"], 0.6)
    assert_close(result["repaired"]["p2"], 0.3)
    assert_close(result["repaired"]["p3"], 0.1)
    assert_close(sum(result["repaired"].values()), 1.0)
    assert result["report"]["steps"][0]["op"] == "minimal_feasible_projection"


def test_fixed_parameter_is_not_changed_during_projection():
    spec = compile_written_constraints(
        """
        variables: x1, x2, x3, cap
        fixed(cap)
        x1, x2, x3 >= 0
        x1 + x2 + x3 <= cap
        """,
        name="budget_demo",
    )

    result = diagnose_and_repair(spec, {"x1": 60, "x2": 50, "x3": 40, "cap": 120})

    assert_close(result["repaired"]["x1"], 50)
    assert_close(result["repaired"]["x2"], 40)
    assert_close(result["repaired"]["x3"], 30)
    assert_close(result["repaired"]["cap"], 120)


def test_attestation_verifies_offline_with_hmac():
    spec = compile_written_constraints("x + y = 1", name="attested_demo")
    result = diagnose_and_repair(spec, {"x": 0.8, "y": 0.4})
    attestation = attest(spec_to_dict(spec), result)

    assert verify_hmac(attestation)
