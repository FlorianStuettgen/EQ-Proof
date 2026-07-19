# Cross-Period Forecast Intelligence

Status: implementation track

Related issue: #12

## Purpose

EQ-Proof currently determines whether one project-controls close is internally defensible under selected equations. The next product layer compares two governed close states and determines which movements are reconciled, which reflect governance changes, and which remain unsupported.

The comparison must answer:

> What changed since the prior close, which movements are supported by governed evidence, and which movements cannot be reconciled?

## Product boundary

This feature extends the existing Control Room. It does not replace or redesign it.

The interaction shell audited in PR #11 is the frozen baseline for this cycle. New comparison views must reuse its visual hierarchy, keyboard behavior, focus management, responsive rules, export conventions, accessibility contract, and interpretation boundaries. Cosmetic redesign is out of scope unless a functional requirement or browser audit proves it necessary.

## Comparison inputs

The first release compares two `eq-proof/control-room@2` artifacts:

- prior period;
- current period.

A later adapter may accept raw P6 XER, cost CSV, and equation packs for each period before invoking the same comparison engine.

Each period must provide:

- reporting-period metadata;
- currency code;
- source SHA-256 manifest;
- equation manifest;
- portfolio reconstruction;
- normalized control-account and activity records;
- findings and gate result.

## Comparability gate

Comparison is blocked when:

- currencies differ and no explicit normalized currency basis is supplied;
- period ordering is invalid or ambiguous;
- schemas are unsupported;
- source identity is insufficient to establish a defensible mapping;
- required portfolio fields are absent;
- an equation-manifest change makes a movement incomparable without explicit governance classification.

Comparison enters review when:

- record identity is partially ambiguous;
- one period lacks optional fields needed for a complete bridge;
- a source or equation changed but remains classifiable;
- records were added, removed, split, merged, or renamed.

Comparison is ready only when every material movement is either reconciled or explicitly classified with no blocker-level ambiguity.

## Identity model

Identity matching must be deterministic and visible.

Priority order:

1. explicit immutable source identifier;
2. exact normalized record identifier within the same source system and record type;
3. explicit user-provided identity map;
4. no match.

The engine must not silently use fuzzy or probabilistic matching. Potential renames may be surfaced as suggestions, but they remain unresolved until explicitly mapped.

Every identity result records:

- prior identifier;
- current identifier;
- record type;
- source system;
- match method;
- match status;
- ambiguity reason;
- user override, when applicable.

## Movement model

For each comparable control account, calculate:

- reported EAC delta;
- actual-cost delta;
- ETC delta;
- defensible EAC delta;
- deterministic forecast-gap delta;
- pending-change delta;
- configured-risk-uplift delta;
- reconstructed risk-adjusted-position delta;
- exposure-above-reported delta;
- baseline amount and authorization changes;
- finding lifecycle changes.

For each comparable activity, calculate only fields explicitly available from both normalized periods, including:

- start and finish movement;
- remaining-duration movement;
- total-float movement;
- progress movement;
- status change;
- baseline date change;
- finding lifecycle changes.

Schedule movement must remain schedule assurance unless a supplied equation explicitly establishes a monetary relationship.

## Reconciliation classes

Every material movement receives exactly one primary class.

### Directly reconciled

The delta is supported by explicit before-and-after source fields under the same applicable governing equation.

### Governance change

The result changed because an equation, applicability condition, baseline, delegated authority, risk configuration, or other governed rule changed.

### Source-structure change

The movement depends on a record addition, removal, rename, split, merge, source migration, or unresolved identity mapping.

### Unreconciled restatement

A submitted summary changed without a sufficient source-field and equation bridge.

### Not comparable

Currency, period metadata, schema, field availability, or governance boundaries prevent a defensible comparison.

The engine must not infer cause merely because two values moved together.

## Finding lifecycle

Findings are matched by:

- equation identifier;
- matched record identity;
- applicability context.

Lifecycle states:

- new;
- persistent;
- worsened;
- improved;
- resolved;
- reclassified by governance change;
- not comparable.

Severity changes and residual movement must be retained separately from lifecycle state.

## Portfolio reconstruction

At portfolio level, report:

- prior and current reported EAC;
- total reported EAC movement;
- reconciled movement;
- governance-driven movement;
- source-structure movement;
- unreconciled movement;
- not-comparable movement;
- prior and current defensible EAC;
- prior and current deterministic forecast gap;
- prior and current declared change and configured risk;
- prior and current reconstructed risk-adjusted position;
- prior and current close gate;
- new, persistent, worsened, improved, and resolved blockers.

The movement bridge must close arithmetically or disclose the exact residual preventing closure.

## Artifact contract

Schema identifier:

`eq-proof/period-comparison@1`

Required top-level sections:

- `schema_version`
- `engine_version`
- `periods`
- `comparability`
- `source_manifests`
- `equation_manifests`
- `identity_map`
- `portfolio_movement`
- `record_movements`
- `finding_lifecycle`
- `governance_changes`
- `unreconciled_movements`
- `comparison_gate`
- `assumptions`

The artifact must remain JSON-safe, deterministic, and byte-stable after canonical generation.

## CLI contract

Proposed command:

```text
eq-controls compare \
  --prior prior-control-room.json \
  --current current-control-room.json \
  --output comparison-output
```

Required outputs:

- `period-comparison.json`
- `movement-register.csv`
- `comparison-brief.md`

Proposed exit codes:

- `0`: comparison ready;
- `2`: comparison review required;
- `3`: comparison blocked;
- `4`: invalid or non-comparable inputs.

## Local API contract

Proposed endpoint:

`POST /api/compare`

The endpoint accepts two Control Room artifacts and an optional explicit identity map. It returns the same comparison schema used by the CLI.

The public GitHub Pages application remains synthetic-only. Real project files remain restricted to the loopback local application.

## Control Room integration

Comparison mode should add, without redesigning the shell:

- a prior/current period selector and clear period labels;
- an executive movement gate;
- a reconciled-versus-unreconciled movement bridge;
- ranked control-account drivers;
- finding-lifecycle filters;
- governance-change register;
- identity-mapping exceptions;
- accessible before/after and delta tables;
- an evidence graph linking both periods to delta equations and the comparison gate;
- comparison brief and movement-register downloads.

## Synthetic showcase

Create a deterministic two-period hyperscale example where:

- reported EAC increases materially;
- part of the movement reconciles to actual cost and ETC;
- part reflects approved pending change;
- one baseline or authority change is governed and visible;
- one forecast restatement remains unsupported;
- one blocker is resolved and another is newly introduced;
- all headline movement numbers trace to source records and equations.

The showcase must avoid invented schedule-to-cost causality and probabilistic claims.

## Test strategy

### Engine

- exact arithmetic movement reconciliation;
- identity mapping and ambiguity handling;
- lifecycle classification;
- equation-manifest changes;
- currency and period incompatibility;
- added, removed, renamed, split, and merged records;
- deterministic output ordering and canonical serialization;
- legacy single-close compatibility.

### CLI and API

- exit-code contract;
- output-package completeness;
- malformed and incompatible artifacts;
- optional identity-map validation;
- request-size and loopback security boundaries.

### Browser

Extend the permanent Playwright audit to cover:

- period selection;
- movement bridge rendering;
- keyboard navigation;
- identity and finding filters;
- empty and non-comparable states;
- exports;
- desktop, mobile, and reduced-motion behavior;
- zero page and console errors;
- serious and critical axe findings.

## Delivery order

1. comparison schema and deterministic engine;
2. identity and lifecycle model;
3. CLI outputs and exit codes;
4. local API;
5. synthetic two-period evidence;
6. Control Room integration;
7. browser audit expansion;
8. documentation and release evidence.

## Definition of done

- every material movement is reconciled or explicitly classified;
- no silent fuzzy identity matching;
- no invented causal or probabilistic claims;
- comparison artifacts regenerate byte-for-byte;
- existing single-close behavior remains backward compatible;
- repository coverage remains above the enforced threshold;
- repository-proof, ui-audit, CodeQL, Pages validation, and production deployment pass;
- the audited UI baseline remains recognizable and functionally consistent.
