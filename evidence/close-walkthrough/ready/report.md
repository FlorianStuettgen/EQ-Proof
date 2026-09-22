# 3. Selected controls satisfied — synthetic evidence

All 32 applicable checks pass. USD 65M of declared change and risk remains visible.

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
| Close owner | Review applicability, source completeness, the USD 65M declared exposure and the remaining schedule/commercial limitations before any approval. |

Owners above are illustrative roles; no task has been assigned to a real person.

## Input changes in this stage

- Financial inputs are identical to the reconciled case.
- CIV-A100: remaining duration 0 to 120 hours; total float -960 to +40 hours in a constructed replacement export.
- These supplied schedule values demonstrate the controls; EQ-Proof did not calculate or validate the revised schedule.

## Applicability and limits

All three supplied authorization limits are checked. One progress-duration check is not applicable because COM-A300 has not started. Missing required fields in other data can also produce not-applicable results and must be reviewed before relying on a gate.

Synthetic inputs illustrate three deliberately constructed states, not an automated repair or a real approval. Ready means no failures among selected, applicable equations; it does not establish completeness, forecast accuracy, schedule feasibility, or authority to close. The risk bridge is arithmetic, not a calculated P80.

## Source bytes

| Source | SHA-256 |
| --- | --- |
| [schedule.xer](../../../examples/close_walkthrough/ready/schedule.xer) | `7385529ef564efe806f0a2775eac7abe20197c069be46a700c76a16f011c7a3e` |
| [cost.csv](../../../examples/close_walkthrough/ready/cost.csv) | `2b96bd66455d9ca8e414103b69ca9bc27e2595dc8bd568bd0fd550ffab1c92ce` |
| [custom_equations.json](../../../examples/close_walkthrough/ready/custom_equations.json) | `fa3ee9df410f411ec82c5cff2df1d958c07e5c0d4da5bea0d7e0e800b9c4d136` |

The JSON exports include the complete executed equation manifest and every pass, failure and not-applicable result.

## Engine report

### Close gate

| Metric | Value |
| --- | ---: |
| Gate | **READY** |
| Records analyzed | 6 |
| Equations executed | 32 |
| Blockers | 0 |
| Total failures | 0 |

### Ranked exception register

| Severity | Record | Equation | Residual | Required action |
| --- | --- | --- | ---: | --- |
| — | — | — | — | No exceptions |

### Operating boundary

The workbench evaluates supplied exports against declared equations. It does not approve changes, infer contractual truth, or convert schedule defects into monetary impacts without an explicit user equation. The output embeds the complete equation manifest and source digests when files were loaded through the native adapters.
