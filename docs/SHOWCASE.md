# Three close decisions, with the evidence to reproduce them

EQ-Proof acts as a compiler for the acceptance logic behind a project close: supplied records and equations become findings, a gate and inspectable evidence. This showcase makes that process concrete for a project-controls leader and a technical reviewer.

[Open the browser workbench](https://florianstuettgen.github.io/EQ-Proof/) · [Source inputs and field changes](../examples/close_walkthrough/README.md) · [Five-minute demo](DEMO_PLAYBOOK.md)

## The decision

A synthetic data-centre project reports a **$407M** estimate at completion (EAC). Its actual cost plus remaining forecast totals **$418M**. The reviewer needs to isolate that **$11M** contradiction, distinguish it from declared change and risk, and see which checks remain unresolved after corrected inputs are supplied.

The three cases below are deliberately constructed source snapshots. EQ-Proof evaluates each snapshot independently; it does not invent corrections, approve changes, or implement cross-period comparison.

| Case | Reported EAC | AC + ETC | Forecast gap | Blockers / all failures | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Blocked | $407M | $418M | $11M | 3 / 5 | CLOSE BLOCKED |
| Review | $418M | $418M | $0 | 0 / 2 | REVIEW REQUIRED |
| Ready | $418M | $418M | $0 | 0 / 0 | CLOSE READY |

All three cases retain **$65M of declared change and configured risk**, producing a **$483M reconstructed risk-adjusted position**. Correcting an arithmetic discrepancy does not remove that declared exposure.

## The 90-second demonstration

1. Select **Try three examples** on the landing page or **Showcase examples** in the workspace. Choose **1. Submitted close** and select **Run example**. The browser compiles the packaged CSV, P6 XER and equation files using the analysis engine.
2. Read the **$11M deterministic forecast gap**. Open `MEP-200`: its $37M position above reported EAC contains a $7M forecast discrepancy, $12M of pending change and $18M of configured risk.
3. Open the **Evidence graph** or **Exceptions**. Follow a finding from its record to the equation, exact input values, residual and required action. A schedule finding remains a schedule-assurance issue, with no invented financial impact.
4. Run **2. Forecast reconciled**. The cost discrepancies are resolved in the supplied inputs; two schedule checks still require attention. A zero forecast gap does not make the gate ready.
5. Run **3. Selected controls satisfied**. In **Controls & coverage**, expand **Inspect a control result** to inspect passed and not-applicable results. Download the brief or analysis JSON. The gate reflects the selected applicable controls, not management approval.

For a guided review of the active result, choose **Take the 90-second tour**. Its six steps cover the decision, forecast, source account, graph, actions and control coverage. The default demo is preserved; the three showcase cases add the explicit authorization inputs needed to execute their custom rule. **Workspace options** contains the reset, JSON reopening and storage controls.

## What changes between cases

The blocked case has two understated EACs and a current-budget bridge that does not match baseline plus approved changes. In the review inputs, those fields and their dependent reported values are supplied consistently. Actual costs, remaining estimates, declared changes and configured risk stay unchanged.

The ready inputs also correct one activity's remaining duration and total float. These are illustrative source edits by the scenario author, not recommended schedule values or engine-generated repairs. The [fixture guide](../examples/close_walkthrough/README.md) lists every changed field.

Each case supplies synthetic delegated-authorization limits for all three control accounts. The user-written `EAC <= delegated_authorization` rule executes and passes in every case. That demonstrates configurable governance logic; it does not evidence a real approval.

## Inspect the outputs without installing anything

| Case | Human-readable result | Action register | Full analysis | Reopenable workspace |
| --- | --- | --- | --- | --- |
| Blocked | [Report](../evidence/close-walkthrough/blocked/report.md) | [CSV](../evidence/close-walkthrough/blocked/exceptions.csv) | [JSON](../evidence/close-walkthrough/blocked/analysis.json) | [Control Room](../evidence/close-walkthrough/blocked/control-room.json) |
| Review | [Report](../evidence/close-walkthrough/review/report.md) | [CSV](../evidence/close-walkthrough/review/exceptions.csv) | [JSON](../evidence/close-walkthrough/review/analysis.json) | [Control Room](../evidence/close-walkthrough/review/control-room.json) |
| Ready | [Report](../evidence/close-walkthrough/ready/report.md) | [CSV](../evidence/close-walkthrough/ready/exceptions.csv) | [JSON](../evidence/close-walkthrough/ready/analysis.json) | [Control Room](../evidence/close-walkthrough/ready/control-room.json) |

Source hashes tie the evidence to the actual input bytes. The analysis retains the equation manifest, per-record findings and applicability results. Each case executes **32 checks** and records **one not-applicable check**: the in-progress activity rule does not apply to the not-started activity. That explicit exclusion remains visible even in the ready case.

## Reproduce the evidence

After the [repository setup](../README.md#run-the-python-application):

```bash
python -m pip install -e '.[dev]'
python scripts/regenerate_showcase_cases.py --check
npm run test:browser-engine
```

The Python generator rebuilds all three cases from source files and checks the committed bytes. Browser-engine tests independently parse those same files and compare gates, portfolio values, source manifests and findings with the Python results. CLI tests verify gate states and exit codes. Browser tests exercise the chooser, actual compilation and downloads.

The exact test count belongs to the validated change and CI record, rather than a permanent showcase claim. See [Development](DEVELOPMENT.md) for the complete validation workflow.

## What the result establishes

- **Arithmetic consistency:** detail-reconstructed EAC is `AC + ETC`; it is not an independent commercial forecast.
- **Declared exposure:** the risk bridge adds supplied amounts; it is not a Monte Carlo simulation or calculated P80.
- **Applicable controls:** missing fields may produce not-applicable results. `CLOSE READY` does not certify complete source data or authorization.
- **Reproducibility:** hashes and deterministic outputs support inspection and replay, not source-system authenticity or contractual truth.

The hosted workbench processes files on the visitor's device and is session-only by default. The Python app processes uploads on loopback in request-scoped temporary storage. [Runtime Modes and Data Handling](RUNTIME_MODES.md) explains the storage and execution boundaries.
