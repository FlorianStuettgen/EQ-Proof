# EQ-Proof Wiki

EQ-Proof is a local-first project-controls Control Room backed by an independently versioned numerical repair and verification engine.

## Start with the operational product

- [Project Controls Workbench](Project-Controls-Workbench) — P6 XER, generic cost exports, tested equations, user rules and close-gate outputs
- [Semantic Model](https://github.com/FlorianStuettgen/EQ-Proof/blob/main/docs/SEMANTIC_MODEL.md) — authoritative financial states, gate meanings, assurance boundary and impact routing
- [Product Architecture](https://github.com/FlorianStuettgen/EQ-Proof/blob/main/docs/PRODUCT_ARCHITECTURE.md) — runtime modes, data flow, security and reproducibility
- [Demo Playbook](https://github.com/FlorianStuettgen/EQ-Proof/blob/main/docs/DEMO_PLAYBOOK.md) — five-minute manager and engineering-panel walkthrough
- [Quickstart](Quickstart) — install, validate, repair and verify

## Core engine

- [Core concepts](Concepts) — feasible sets, fixed values and minimal change
- [Specification language](Specification-Language) — JSON fields and equation grammar
- [Proof and verification](Proof-and-Verification) — integrity, signatures and semantic replay
- [Architecture](Architecture) — modules, data flow and invariants
- [Security model](Security-Model) — threats, controls and trust boundary
- [Development](Development) — tests, evidence, benchmarks and release workflow

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
