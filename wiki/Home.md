# EQ-Proof Wiki

EQ-Proof is a local-first project-controls Control Room backed by an independently versioned numerical repair and verification engine.

## Start with the operational product

- [Project Controls Workbench](Project-Controls-Workbench.md) — P6 XER, generic cost exports, tested equations, user rules and close-gate outputs
- [Semantic Model](../docs/SEMANTIC_MODEL.md) — authoritative financial states, gate meanings, assurance boundary and impact routing
- [Product Architecture](../docs/PRODUCT_ARCHITECTURE.md) — runtime modes, data flow, security and reproducibility
- [Demo Playbook](../docs/DEMO_PLAYBOOK.md) — five-minute manager and engineering-panel walkthrough
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
P6 XER TASK + generic cost CSV + catalogue + user equations
                              ↓
                deterministic field normalization
                              ↓
           applicability + safe equation evaluation
                              ↓
       source hashes + ranked findings + equation manifest
                              ↓
 reported EAC / defensible EAC / risk-adjusted reconciliation
                              ↓
      declared evidence graph + close gate + action exports
```

The Control Room does not replace P6, the cost system, probabilistic risk modelling or professional judgment. It makes declared acceptance logic explicit, reusable and testable without inventing causal or financial relationships that were not encoded.
