# Control Room semantic model

This document is the vocabulary contract for EQ-Proof project-controls outputs. Code, UI, examples, reports and documentation should use these terms consistently. Machine-field compatibility is distinguished from visitor-facing labels where an existing schema name carries a stronger implication than the calculation supports.

## Financial states

### Reported EAC

The submitted deterministic estimate at completion.

```text
reported_eac = submitted EAC
```

EQ-Proof treats this as a source claim. It is never silently replaced.

### Detail-reconstructed EAC

The deterministic EAC reconstructed from available actual cost and estimate-to-complete detail.

```text
detail-reconstructed EAC = AC + ETC
```

The current `eq-proof/control-room@2` schema retains the field name `defensible_eac` for compatibility. User-facing interfaces and new documentation call the same value **detail-reconstructed EAC**.

This value establishes an internal arithmetic reconciliation. It does not independently establish commercial defensibility, forecast quality, management approval, contractual correctness or the most likely final outcome.

### Deterministic forecast gap

The contradiction between submitted EAC and its governed components.

```text
deterministic_forecast_gap = detail-reconstructed EAC - reported EAC
```

A positive value means the submitted EAC is below `AC + ETC`. This is the strongest dollar-valued inconsistency EQ-Proof can establish from the declared deterministic fields alone.

### Configured change and risk

The sum of explicitly supplied pending-change exposure and risk uplift.

```text
configured_change_and_risk = pending_change_exposure + risk_exposure
```

`risk_exposure` is treated as a configured source value. EQ-Proof does not infer or certify its probability basis.

### Reconstructed risk-adjusted EAC

A declared bridge built from detail-reconstructed EAC plus supplied change and risk fields.

```text
reconstructed_risk_adjusted_eac =
    detail-reconstructed EAC
    + pending_change_exposure
    + risk_exposure
```

This is not a statistical P80 calculation. A source column named `P80_EAC` is accepted as a compatibility alias for a submitted risk-adjusted summary, but EQ-Proof does not certify the percentile methodology that produced it.

### Submitted risk-adjusted EAC

The risk-adjusted summary supplied by the source export, when present for every reconstructed account.

If coverage is incomplete, the portfolio total is `null`; EQ-Proof does not fabricate a partial portfolio summary.

### Risk-adjusted reconciliation gap

The difference between the declared bridge and the submitted risk-adjusted summary.

```text
risk_adjusted_reconciliation_gap =
    reconstructed_risk_adjusted_eac
    - submitted_risk_adjusted_eac
```

### Exposure above reported EAC

A comparison between the reconstructed risk-adjusted position and submitted deterministic EAC.

```text
exposure_above_reported_eac =
    reconstructed_risk_adjusted_eac
    - reported_eac
```

This value combines two logically different components:

1. deterministic forecast contradiction; and
2. declared pending-change and configured-risk exposure.

It must not be labelled entirely as hidden, unsupported or erroneous.

## Gate states

| State | Meaning |
| --- | --- |
| `blocked` | At least one blocker equation failed. |
| `review` | No blocker failed, but one or more lower-severity equations failed. |
| `ready` | No equation failed among the controls that were selected and applicable. |

`ready` means internally consistent under the executed controls. It does not mean contractually correct, complete, approved or risk-free.

CLI automation can choose a stricter threshold with `--fail-on blocker|major|minor|info|never`.

## Control severity index

The current schema retains `assurance.score` and `assurance.label` for compatibility. The interface presents the number as a **control severity index**, not an assurance percentage.

The index is a deterministic finding-weight heuristic used for triage:

```text
100
- 18 per blocker
- 7 per major
- 2 per minor
- 1 per info finding
```

It is bounded from 0 to 100. The weights are transparent engineering defaults, not empirically calibrated outcome weights. The index is not:

- a probability;
- a confidence interval;
- a forecast-accuracy estimate;
- a statistically calibrated risk score;
- a contractual assurance opinion; or
- a substitute for the gate, severity counts, affected domains and material residuals.

Consumers should treat the gate state and individual findings as primary. The combined index is a secondary ordering aid. A future schema revision should rename the machine field if that can be done without ambiguous compatibility behavior.

## Finding applicability

A finding can be:

- `pass` — the equation executed and held within tolerance;
- `fail` — the equation executed and did not hold; or
- `not_applicable` — required fields were unavailable, the record type differed or the optional applicability predicate did not match.

`not_applicable` is not a pass.

## Impact routing

The evidence graph uses declared domains rather than invented causality:

| Equation domain | Declared impact |
| --- | --- |
| cost | deterministic forecast gap |
| risk | risk-adjusted reconciliation |
| change | baseline governance |
| earned value | earned-value assurance |
| schedule | schedule assurance |
| other/custom | close gate unless another mapping is explicitly implemented |

All failed equations can affect the gate. Non-financial findings do not receive a dollar impact without an explicit user equation that supplies one.

## Units

Every Control Room payload includes a three-letter currency code and duration unit. Currency is a display and interpretation label; EQ-Proof does not perform foreign-exchange conversion.

## Reproducibility boundary

Native adapters record SHA-256 source digests. Analysis outputs embed the complete executed equation manifest and all findings. This supports deterministic replay of EQ-Proof's declared checks when the same source files, equation manifest and engine version are available.

It does not prove that source records were truthful, authorized or complete before ingestion.

## Runtime and persistence vocabulary

A **hosted browser analysis** executes in the visitor's browser and does not upload project files to EQ-Proof. It is session-only by default. A **remembered browser workspace** is the complete Control Room JSON stored in browser local storage after explicit opt-in. A **local Control Room analysis** executes through the loopback Python application and uses request-scoped temporary files.

The canonical data-handling definitions are in [Runtime Modes and Data Handling](RUNTIME_MODES.md).
