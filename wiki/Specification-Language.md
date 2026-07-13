# Specification language

A specification contains:

- `schema_version` — currently `1.0`;
- `name` and optional description/metadata;
- ordered variables with bounds, labels, units, and fixed status;
- linear equations with stable IDs.

Supported relations are `==`, `<=`, and `>=`. Terms may use addition, subtraction, parentheses, and multiplication/division by finite scalars.

Nonlinear terms, calls, attributes, imports, powers, chained comparisons, undeclared names, and unknown fields are rejected.

The complete contract is in `schemas/specification.schema.json`, with semantic rules documented in `docs/SPECIFICATION.md`.
