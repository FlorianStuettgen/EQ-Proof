# Changelog

## 1.0.0 — 2026-07-13

- Reconstructed the repository around a single `src/eq_proof` package.
- Added a safe AST-based compiler for linear `==`, `<=`, and `>=` equations.
- Added Euclidean projection through Dykstra's algorithm with bounds and fixed variables.
- Added deterministic JSON proof artifacts, SHA-256 integrity, and Ed25519 attestation.
- Added one CLI for key generation, repair, reporting, and verification.
- Added reproducible evidence, architecture documentation, threat boundaries, and CI across Python 3.10–3.13.
- Added a 54-test quality gate with measured branch coverage above 96% at reconstruction time.
