import math
from dataclasses import replace

from eq_proof import parse_specification, repair
from eq_proof.proof import build_proof


def test_computed_proof_numbers_are_stable_across_one_ulp_differences():
    specification = parse_specification(
        {
            "schema_version": "1.0",
            "name": "stable-proof-sample",
            "variables": {"x": {"lower": 0}, "y": {"lower": 0}},
            "equations": [{"id": "total", "expression": "x + y == 1"}],
        }
    )
    result = repair(specification, {"x": 0.8, "y": 0.5})
    shifted = replace(
        result,
        movement_l2=math.nextafter(result.movement_l2, math.inf),
        objective_value=math.nextafter(result.objective_value, math.inf),
        max_violation_before=math.nextafter(
            result.max_violation_before, math.inf
        ),
        checks_before=tuple(
            replace(
                item,
                lhs=math.nextafter(item.lhs, math.inf),
                violation=math.nextafter(item.violation, math.inf),
            )
            for item in result.checks_before
        ),
    )
    original_proof = build_proof(
        specification,
        result,
        created_utc="2026-01-01T00:00:00Z",
    )
    shifted_proof = build_proof(
        specification,
        shifted,
        created_utc="2026-01-01T00:00:00Z",
    )
    assert original_proof == shifted_proof
    assert original_proof["engine"]["version"] == "1.4.0"
