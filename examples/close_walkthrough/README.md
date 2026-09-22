# A monthly close, in three inspectable states

Follow the same synthetic USD data-centre close from an inconsistent submission to a state where the selected controls pass. Every stage includes three control accounts, three P6 activities and one project-specific authorization rule. Open a stage in the browser workbench, inspect its source files, or reproduce its evidence locally.

| Example | Gate | What a reviewer learns | Blockers / failures |
| --- | --- | --- | ---: |
| [Submitted close](../../evidence/close-walkthrough/blocked/report.md) | **Blocked** | USD 407M reported EAC does not reconcile to USD 418M of AC + ETC. | 3 / 5 |
| [Forecast reconciled](../../evidence/close-walkthrough/review/report.md) | **Review required** | The USD 11M forecast gap is gone; two schedule findings remain. | 0 / 2 |
| [Selected controls satisfied](../../evidence/close-walkthrough/ready/report.md) | **Ready within scope** | All 32 applicable checks pass; USD 65M of declared change and risk remains. | 0 / 0 |

The stages are deliberately constructed inputs. EQ-Proof does not repair these exports, calculate revised schedule dates, approve changes or authorize a close.

## Read the decision before the implementation

The submitted close reports USD 407M of forecast at completion. Actual cost plus estimate to complete totals USD 418M. The USD 11M difference consists of USD 4M in `CIV-100` and USD 7M in `MEP-200`.

A separate USD 65M comprises USD 26M of pending change and USD 39M of configured risk uplift. The detail-based arithmetic bridge is therefore USD 483M. That is USD 76M above the submitted USD 407M forecast, but only USD 11M is a deterministic forecast contradiction. It is not a probabilistic P80 calculation.

The first stage also contains a USD 5M budget-bridge failure in `MEP-200` and two schedule findings in `CIV-A100`. Schedule findings are not assigned a dollar impact.

## Exactly what changes

All three stages supply fictional delegated EAC limits of USD 135M for `CIV-100`, USD 200M for `MEP-200` and USD 100M for `COM-300`. The custom authorization equation executes and passes for every account. These fields distinguish the walkthrough from the original hyperscale fixture, which does not supply authorization limits.

From **blocked** to **review**, the illustrative cost-controller corrections are:

| Source record / field | Submitted | Reconciled |
| --- | ---: | ---: |
| `CIV-100` / EAC | 126M | 130M |
| `CIV-100` / VAC | -6M | -10M |
| `CIV-100` / risk-adjusted EAC | 146M | 150M |
| `MEP-200` / EAC | 188M | 195M |
| `MEP-200` / VAC | -8M | -15M |
| `MEP-200` / risk-adjusted EAC | 218M | 225M |
| `MEP-200` / current budget | 185M | 180M |

The current-budget correction follows the supplied baseline of 165M plus approved changes of 15M. It is a constructed data correction, not evidence that any real budget movement was authorized. Actual cost, ETC, pending change, configured risk and schedule inputs do not change in this step.

From **review** to **ready**, the cost file is byte-identical. Only `CIV-A100` changes in the replacement schedule export: remaining duration increases from 0 to 120 hours, and total float moves from -960 to +40 hours. These are supplied demonstration values. The P6 `TASK` adapter cannot establish the feasibility of that movement from schedule relationships, calendars or constraints. `MEP-A200` still has -240 hours of float; it passes the starter -800-hour review threshold, which is not a contractual limit.

## Applicability matters

Each stage executes 32 checks and records one **not applicable** result: the remaining-duration rule does not apply to not-started activity `COM-A300`. No authorization check is skipped in these examples.

With other inputs, missing required fields can also make an equation not applicable. **Ready** means that none of the selected, applicable equations failed; it does not establish source completeness, commercial correctness or approval. The compatibility field `analysis.close_ready` means "no blockers" and can be true during **review**. Use `gate.status` or `analysis.gate_status` for the full three-state decision.

## Reproduce a stage

From the repository root, install the package with `python -m pip install -e .`, then run:

```text
eq-controls analyze --p6-xer examples/close_walkthrough/blocked/schedule.xer --cost-csv examples/close_walkthrough/blocked/cost.csv --equations examples/close_walkthrough/blocked/custom_equations.json --currency USD --output outputs/walkthrough-blocked
```

Replace all three `blocked` directory names with `review` or `ready` to run another stage. The command produces `analysis.json`, `control-room.json`, `exceptions.csv` and `report.md`.

By default the CLI returns exit code **3** for blocked and **0** for review or ready, because its default failure threshold is blocker. Add `--fail-on minor` to return **3** for the review stage as well. A successful process exit is not a close approval.

The checked-in reports add scenario context to the CLI's engine report. Their JSON and exception registers are generated from the same engine output. Published `control-room.json` workspaces also include `demo` metadata identifying the scenario as synthetic, so opening one in the browser preserves its example identity for exports. This presentation metadata does not change the gate, calculations or findings. Rebuild or verify all published evidence with:

```text
python scripts/regenerate_showcase_cases.py
python scripts/regenerate_showcase_cases.py --check
```

The browser manifest embeds the exact UTF-8/LF bytes of every source, with SHA-256 digests. The browser compiles those inputs through its own engine; Python and JavaScript tests compare the results against known amounts, gates, applicability and source hashes. This demonstrates reproducibility against supplied inputs, not independent assurance of the inputs.
