# 2. Forecast reconciled — synthetic evidence

The USD 11M arithmetic gap is resolved. Two schedule findings still require review.

## Reconstructed position

All values are synthetic USD; no currency conversion is performed.

| Measure | USD |
| --- | ---: |
| Reported EAC | 418,000,000 |
| Detail-reconstructed EAC (AC + ETC) | 418,000,000 |
| Deterministic forecast gap | 0 |
| Declared change and configured risk | 65,000,000 |
| Reconstructed risk-adjusted position | 483,000,000 |
| Submitted risk-adjusted summary | 483,000,000 |
| Risk-adjusted reconciliation gap | 0 |
| Position above reported EAC | 65,000,000 |

## Suggested review actions

| Suggested owner | Action |
| --- | --- |
| Scheduler | Review CIV-A100's status, remaining work and driving schedule logic; arithmetic checks cannot establish a feasible schedule. |

Owners above are illustrative roles; no task has been assigned to a real person.

## Input changes in this stage

- CIV-100: EAC 126M to 130M; VAC -6M to -10M; submitted risk-adjusted EAC 146M to 150M.
- MEP-200: EAC 188M to 195M; VAC -8M to -15M; submitted risk-adjusted EAC 218M to 225M.
- MEP-200: current budget 185M to 180M, matching the supplied baseline plus approved changes.
- Schedule inputs are unchanged; financial reconciliation alone does not clear the schedule review.

## Applicability and limits

All three supplied authorization limits are checked. One progress-duration check is not applicable because COM-A300 has not started. Missing required fields in other data can also produce not-applicable results and must be reviewed before relying on a gate.

Synthetic inputs illustrate three deliberately constructed states, not an automated repair or a real approval. Ready means no failures among selected, applicable equations; it does not establish completeness, forecast accuracy, schedule feasibility, or authority to close. The risk bridge is arithmetic, not a calculated P80.

## Source bytes

| Source | SHA-256 |
| --- | --- |
| [schedule.xer](../../../examples/close_walkthrough/review/schedule.xer) | `233486f70f5a4ee98c6fcac046515148b28b4256e5d61466146324359c6b888a` |
| [cost.csv](../../../examples/close_walkthrough/review/cost.csv) | `2b96bd66455d9ca8e414103b69ca9bc27e2595dc8bd568bd0fd550ffab1c92ce` |
| [custom_equations.json](../../../examples/close_walkthrough/review/custom_equations.json) | `fa3ee9df410f411ec82c5cff2df1d958c07e5c0d4da5bea0d7e0e800b9c4d136` |

The JSON exports include the complete executed equation manifest and every pass, failure and not-applicable result.

## Engine report

### Close gate

| Metric | Value |
| --- | ---: |
| Gate | **REVIEW REQUIRED** |
| Records analyzed | 6 |
| Equations executed | 32 |
| Blockers | 0 |
| Total failures | 2 |

### Ranked exception register

| Severity | Record | Equation | Residual | Required action |
| --- | --- | --- | ---: | --- |
| `major` | `CIV-A100` | `schedule.progress_duration` | `0` | Correct activity status, actual finish or remaining duration in P6. |
| `minor` | `CIV-A100` | `schedule.extreme_negative_float` | `160` | Replace the starter threshold with a project-specific equation, then review constraints, calendars and driving relationships. |

### Operating boundary

The workbench evaluates supplied exports against declared equations. It does not approve changes, infer contractual truth, or convert schedule defects into monetary impacts without an explicit user equation. The output embeds the complete equation manifest and source digests when files were loaded through the native adapters.
