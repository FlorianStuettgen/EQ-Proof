# Changelog

All notable changes are documented here. The Python package follows semantic versioning; proof, specification and Control Room payload contracts are versioned independently when their semantics change.

## Unreleased

### Added

- Guided five-step, 90-second Control Room tour covering the gate, deterministic contradiction, material account, evidence lineage and action register.
- Dynamic executive-story reconstruction on the public landing page.
- Downloadable Markdown executive close brief containing portfolio states, ranked actions and source SHA-256 evidence.
- Portfolio case study focused on the operational decision, product boundary and engineering proof.
- Visible engineering-evidence strip covering automated tests, Python runtimes, telemetry, deterministic evidence and coverage enforcement.

### Changed

- Rebuilt the README as a product-first showcase with a direct guided-demo path.
- Expanded social metadata, responsive presentation, call-to-action hierarchy and reduced-motion behavior.
- Added the showcase JavaScript module to local and hosted repository validation.

## 1.4.0 — 2026-07-14

### Changed

- Replaced the ambiguous `$76M hidden exposure` claim with separate deterministic, declared-exposure and risk-adjusted reconciliation states.
- Renamed `Defensible P80` to `Reconstructed risk-adjusted position`; deterministic addition is no longer presented as a probabilistic percentile calculation.
- Introduced `eq-proof/control-room@2` and an authoritative semantic model.
- Added distinct `blocked`, `review`, and `ready` gate states plus configurable CLI failure thresholds.
- Routed schedule findings to schedule assurance rather than inventing dollar impacts.
- Made incomplete submitted risk-adjusted coverage explicit instead of summing misleading partial totals.
- Replaced legacy browser modules with purpose-named renderer and workflow modules.
- Normalized computed proof outputs to 15 significant digits before attestation, eliminating one-ULP evidence drift across supported numerical environments while preserving submitted and specification values exactly.
- Advanced the lower proof engine implementation version to `1.4.0` without changing `proof@1` or `dykstra-l2-v1`; existing artifacts remain verifiable.

### Added

- Source SHA-256 manifest and complete equation manifest in analysis outputs.
- `control-room.json` CLI output, explicit currency labels, equation validation endpoint and downloadable equation packs.
- Optional equation applicability predicates.
- Exception filters, graph truncation reporting and static-versus-local UX boundaries.
- Tests for malformed equations, resource limits, incomplete summaries, non-finite arithmetic, trusted hosts, CSV formula injection, semantic routing and one-ULP proof stability.
- CI failure artifacts containing exact deterministic-evidence drift for reproducibility debugging.

### Security

- Loopback-only host choices and trusted-host enforcement.
- 200 MiB aggregate request and 20-file limits in addition to the 50 MiB per-file limit.
- Equation-count, expression-size, AST-node and adapter-row limits.
- JSON-safe non-finite findings and spreadsheet-formula neutralization in CSV exports.

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

- `eq-controls serve` launches the real-file browser application on loopback.
- The repository's primary product positioning is project-controls close assurance.
- Package version and documentation advanced to 1.3.0; the numerical proof artifact remained independently versioned where its contract did not change.

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

- Proofs record objective value, maximum iteration budget, and stable algorithm identifier.
- Verification distinguishes integrity, authenticity, and semantic correctness.
- Unknown configuration fields and Python-keyword variable names are rejected.
- Syntax complexity limits support legitimate higher-dimensional linear models while retaining abuse controls.

### Security

- A false numerical result is rejected even when its artifact is internally rehashed or validly signed.

## 1.0.0 — 2026-07-13

- Initial reconstructed package with safe linear compilation, Euclidean repair, deterministic proof artifacts, Ed25519 attestation, examples, and CI.
