# Control Room Semantic Model

This document is the vocabulary contract for EQ-Proof project-controls outputs. Code, UI, examples, reports and documentation should use these terms consistently.

## Financial states

### Reported EAC

The submitted deterministic estimate at completion.

```text
reported_eac = submitted EAC
```

EQ-Proof treats this as a source claim. It is never silently replaced.

### Defensible EAC

The deterministic EAC reconstructed from governed detail when actual cost and estimate to complete are both available.

```text
defensible_eac = AC + ETC
```

This is an internal arithmetic reconciliation, not a prediction of the commercially correct outcome.

### Deterministic forecast gap

The contradiction between submitted EAC and its governed components.

```text
deterministic_forecast_gap = defensible_eac - reported_eac
```

A positive value means the submitted EAC is below `AC + ETC`. This is the strongest dollar-valued inconsistency EQ-Proof can establish from the declared deterministic fields alone.

### Configured change and risk

The sum of explicitly supplied pending-change exposure and risk uplift.

```text
configured_change_and_risk = pending_change_exposure + risk_exposure
```

`risk_exposure` is treated as a configured source value. EQ-Proof does not infer its probability basis.

### Reconstructed risk-adjusted EAC

A declared bridge built from defensible EAC plus supplied change and risk fields.

```text
reconstructed_risk_adjusted_eac =
    defensible_eac
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

## Assurance score

The displayed assurance score is a deterministic severity-penalty heuristic used for triage:

```text
100
- 18 per blocker
- 7 per major
- 2 per minor
- 1 per info finding
```

It is bounded from 0 to 100. It is not a probability, confidence interval, forecast accuracy estimate or statistically calibrated risk score.

## Finding applicability

A finding can be:

- `pass` — the equation executed and held within tolerance;
- `fail` — the equation executed and did not hold;
- `not_applicable` — required fields were unavailable, the record type differed, or the optional applicability predicate did not match.

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
