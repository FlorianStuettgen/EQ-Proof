# EQ-Proof Wiki

EQ-Proof is a project-controls equation workbench backed by a generic repair and verification engine.

## Start with the operational product

- [Project Controls Workbench](Project-Controls-Workbench.md) — P6 XER, cost exports, tested equations, user rules and close-gate outputs
- [Quickstart](Quickstart.md) — install, validate, repair and verify

## Core engine

- [Core concepts](Concepts.md) — feasible sets, fixed values and minimal change
- [Specification language](Specification-Language.md) — JSON fields and equation grammar
- [Proof and verification](Proof-and-Verification.md) — integrity, signatures and semantic replay
- [Architecture](Architecture.md) — modules, data flow and invariants
- [Security model](Security-Model.md) — threats, controls and trust boundary
- [Development](Development.md) — tests, evidence, benchmarks and release workflow

## Mental model

```text
P6 XER + cost/control exports + equation catalogue + user equations
                              ↓
                    canonical field mapping
                              ↓
                  applicable equation selection
                              ↓
                 ranked controls exceptions
                              ↓
           close gate + CSV + JSON + review report
                              ↓
       optional constrained repair and proof attestation
```

The workbench does not replace P6, the cost system or professional judgment. It makes the acceptance logic between those systems explicit, reusable and testable.
