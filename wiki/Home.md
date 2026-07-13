# EQ-Proof Wiki

EQ-Proof turns declared numeric rules into an executable repair-and-verification contract.

## Start here

- [Quickstart](Quickstart.md) — install, validate, repair, verify
- [Core concepts](Concepts.md) — feasible sets, fixed values, minimal change
- [Specification language](Specification-Language.md) — JSON fields and equation grammar
- [Proof and verification](Proof-and-Verification.md) — integrity, signatures, semantic replay
- [Architecture](Architecture.md) — modules, data flow, invariants
- [Security model](Security-Model.md) — threats, controls, trust boundary
- [Development](Development.md) — tests, evidence, benchmarks, release workflow

## Mental model

```text
rules + submitted values
        ↓
diagnose violations
        ↓
nearest feasible repair
        ↓
canonical proof + optional signature
        ↓
independent semantic replay
```

The JSON proof is authoritative. Reports and visuals are derived views.
