# Changelog

All notable changes are documented here. The project follows semantic versioning for the Python package; proof and specification contracts are versioned independently inside artifacts.

## 1.3.0 — 2026-07-14

### Added

- Local-first **EQ-Proof Control Room** web application.
- Executive close gate with reported, defensible, and risk-adjusted portfolio states.
- Account-level surprise decomposition and interactive evidence graph.
- Ranked exception command centre with CSV export.
- Browser equation catalogue and project-specific equation editor.
- FastAPI upload boundary for P6 XER, cost CSV, and equation-pack files.
- Static synthetic demo suitable for GitHub Pages.
- Product architecture and five-minute panel/manager demo playbook.

### Changed

- `eq-controls serve` now launches the real-file browser application on loopback.
- The repository's primary product positioning is project-controls close assurance.
- Public evidence now reconstructs a deterministic $76M hidden-exposure scenario.
- Package version, proof engine version, signed evidence, and documentation advance to 1.3.0.

### Security

- Real-file mode uses request-scoped temporary directories, a 50 MiB per-file limit, path-basename normalization, restrictive browser headers, no telemetry, and no external frontend dependencies.

## 1.2.0 — 2026-07-13

### Added

- Native Primavera P6 XER `TASK` ingestion.
- Cost/control-account CSV alias mapping.
- Tested project-controls equation catalogue spanning cost, EVM, change, risk, and schedule assurance.
- User-supplied equation packs and `eq-controls` CLI.
- Hyperscale close fixture, exception CSV, and close-gate exit codes.

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
