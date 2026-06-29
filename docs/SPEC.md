# Spec Format

An EQ-PROOF spec is JSON with these top-level fields:

- `name`: spec name.
- `version`: spec version.
- `variables`: numeric variables repaired or attested by the engine.
- `units`: optional map from variable name to canonical unit string; use `"1"` for dimensionless values.
- `fixed`: optional list of variables that must stay equal to their input values.
- `constraints`: ordered list of constraints.
- `probes`: optional expressions retained for audit context.
- `alternates`: optional labels for alternate model or policy choices.

Supported constraint types:

- `bounds`: `{"type": "bounds", "var": "x", "lower": 0, "upper": 1}`
- `linear_eq`: `{"type": "linear_eq", "coeffs": {"x": 1, "y": 1}, "rhs": 1}`
- `linear_leq`: `{"type": "linear_leq", "coeffs": {"x": 1, "y": 1}, "rhs": 1}`
- `equality`: `{"type": "equality", "expr": "Eq(E, h*f)", "solve_for": "E"}`
- `sum_leq`: `{"type": "sum_leq", "vars": ["x1", "x2"], "cap": 100}`
- `simplex`: `{"type": "simplex", "vars": ["p1", "p2", "p3"]}`
- `monotone`: `{"type": "monotone", "vars": ["q1", "q2", "q3"]}`

The written-constraint compiler accepts lines like:

```text
variables: p1, p2, p3
0 <= p1 <= 1
p1 + p2 + p3 = 1
simplex(wA, wB, wC)
fixed(cap)
x1 + x2 + x3 <= cap
```
