# Changelog

All notable changes are documented here. The project follows semantic versioning for the Python package; proof and specification contracts are versioned independently inside artifacts.

## 1.1.0 — 2026-07-13

### Added

- Independent semantic replay during proof verification.
- Explicit compiler, specification, diagnostics, solver, proof, API, and domain layers.
- `validate` CLI command with a dedicated constraint-violation exit code.
- High-level Python API for repair, proof creation, and verification.
- Published JSON Schemas for specifications and proofs.
- Atomic output writes and restrictive private-key permissions.
- Capacity-planning example, benchmark methodology, ADRs, threat model, and version-controlled wiki source.

### Changed

- Proofs now record objective value, maximum iteration budget, and stable algorithm identifier.
- Verification distinguishes integrity, authenticity, and semantic correctness.
- Unknown configuration fields and Python-keyword variable names are rejected.
- Syntax complexity limits support legitimate higher-dimensional linear models while retaining abuse controls.

### Security

- A false numerical result is rejected even when its artifact is internally rehashed or validly signed.

## 1.0.0 — 2026-07-13

- Initial reconstructed package with safe linear compilation, Euclidean repair, deterministic proof artifacts, Ed25519 attestation, examples, and CI.
