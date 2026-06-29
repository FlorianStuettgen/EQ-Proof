# Architecture

EQ-PROOF is organized as a small offline pipeline:

1. `compiler.py` converts written linear constraints into a JSON-compatible spec.
2. `units.py` coerces input values into canonical spec units.
3. `projection.py` projects linear specs onto the feasible set with minimal Euclidean change.
4. `diagnose.py` falls back to symbolic repair for nonlinear equalities when a full linear projection is not possible.
5. `attest.py` signs the proof payload locally.
6. `verify.py` verifies proof signatures locally.
7. `report.py` renders Markdown and PDF-friendly report text.

Linear projection uses Dykstra projections over hyperplanes and halfspaces. Bounds, simplex, monotone, fixed variables, and linear relations are all represented as affine sets. The result is the closest feasible vector in L2 distance up to numerical tolerance.
