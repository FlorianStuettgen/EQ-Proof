# 1. Submitted close — synthetic evidence

USD 407M reported; detail reconstructs to USD 418M. Three blockers stop the close.

## Reconstructed position

All values are synthetic USD; no currency conversion is performed.

| Measure | USD |
| --- | ---: |
| Reported EAC | 407,000,000 |
| Detail-reconstructed EAC (AC + ETC) | 418,000,000 |
| Deterministic forecast gap | 11,000,000 |
| Declared change and configured risk | 65,000,000 |
| Reconstructed risk-adjusted position | 483,000,000 |
| Submitted risk-adjusted summary | 472,000,000 |
| Risk-adjusted reconciliation gap | 11,000,000 |
| Position above reported EAC | 76,000,000 |

## Suggested review actions

| Suggested owner | Action |
| --- | --- |
| Cost lead | Reconcile CIV-100's USD 4M and MEP-200's USD 7M EAC shortfalls to AC + ETC. |
| Change controller | Reconcile MEP-200's USD 5M budget movement to approved change. |
| Scheduler | Review CIV-A100's zero remaining duration and -960 hours of float. |

Owners above are illustrative roles; no task has been assigned to a real person.

## Input changes in this stage

- Original inconsistent forecast and budget, with explicit synthetic authorization limits.

## Applicability and limits

All three supplied authorization limits are checked. One progress-duration check is not applicable because COM-A300 has not started. Missing required fields in other data can also produce not-applicable results and must be reviewed before relying on a gate.

Synthetic inputs illustrate three deliberately constructed states, not an automated repair or a real approval. Ready means no failures among selected, applicable equations; it does not establish completeness, forecast accuracy, schedule feasibility, or authority to close. The risk bridge is arithmetic, not a calculated P80.

## Source bytes

| Source | SHA-256 |
| --- | --- |
| [schedule.xer](../../../examples/close_walkthrough/blocked/schedule.xer) | `233486f70f5a4ee98c6fcac046515148b28b4256e5d61466146324359c6b888a` |
| [cost.csv](../../../examples/close_walkthrough/blocked/cost.csv) | `803ce085c40b024787fd83d35c05b9582590341560ad4ffcf7fab0d28842d588` |
| [custom_equations.json](../../../examples/close_walkthrough/blocked/custom_equations.json) | `fa3ee9df410f411ec82c5cff2df1d958c07e5c0d4da5bea0d7e0e800b9c4d136` |

The JSON exports include the complete executed equation manifest and every pass, failure and not-applicable result.

## Engine report

### Close gate

| Metric | Value |
| --- | ---: |
| Gate | **BLOCKED** |
| Records analyzed | 6 |
| Equations executed | 32 |
| Blockers | 3 |
| Total failures | 5 |

### Ranked exception register

| Severity | Record | Equation | Residual | Required action |
| --- | --- | --- | ---: | --- |
| `blocker` | `MEP-200` | `cost.eac_identity` | `-7e+06` | Reconcile the cost ledger and forecast detail; do not post the close until the identity holds. |
| `blocker` | `MEP-200` | `change.budget_bridge` | `5e+06` | Locate unauthorized budget movement or missing approved change records. |
| `blocker` | `CIV-100` | `cost.eac_identity` | `-4e+06` | Reconcile the cost ledger and forecast detail; do not post the close until the identity holds. |
| `major` | `CIV-A100` | `schedule.progress_duration` | `0` | Correct activity status, actual finish or remaining duration in P6. |
| `minor` | `CIV-A100` | `schedule.extreme_negative_float` | `160` | Replace the starter threshold with a project-specific equation, then review constraints, calendars and driving relationships. |

### Operating boundary

The workbench evaluates supplied exports against declared equations. It does not approve changes, infer contractual truth, or convert schedule defects into monetary impacts without an explicit user equation. The output embeds the complete equation manifest and source digests when files were loaded through the native adapters.
