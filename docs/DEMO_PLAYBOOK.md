# Five-minute Control Room walkthrough

For project-controls leaders and technical reviewers. Use only the supplied synthetic examples for this walkthrough.

[Open the application](https://florianstuettgen.github.io/EQ-Proof/) · [Worked case and evidence](SHOWCASE.md) · [Exact source changes](../examples/close_walkthrough/README.md)

## 0:00–0:45 — Start with the decision

Select **Try three examples** on the landing page or **Showcase examples** in the workspace. In **Examples**, select **1. Submitted close** under **Example case**, and choose **Run example**. **Analyze files** opens the separate **Your files** view for user-supplied inputs.

Explain: the application reads the supplied source files and runs the controls. The gate is computed, not selected by the presenter. Running an example replaces the active analysis with that synthetic case.

The initial result is **CLOSE BLOCKED**, with three blockers and five failures across six source records.

## 0:45–1:45 — Separate contradiction from exposure

Show the submitted **$407M** EAC and **$418M detail-reconstructed EAC** (`AC + ETC`). The **$11M** difference is an arithmetic forecast contradiction.

The **$65M** of declared pending change and configured risk is separate. Adding it to the source detail yields a **$483M** risk-adjusted position, **$76M** above the submitted forecast. The submitted risk-adjusted summary is **$472M**, leaving its own **$11M** reconciliation gap.

Open `MEP-200`: its $37M position above reported EAC comprises $7M of forecast discrepancy, $12M of pending change and $18M of configured risk.

Say what the calculation establishes: the supplied fields disagree. It does not establish that the reconstructed number is commercially correct, or calculate a probabilistic P80.

## 1:45–2:45 — Inspect a finding

Open **Evidence graph** and inspect a cost finding. Follow:

```text
source record → failed equation → declared metric or assurance domain → close gate
```

In **Exceptions**, inspect the equation ID, input values, residual and prescribed remediation. **Export all exceptions** downloads the complete register, regardless of the current display filters. On small screens, the graph scrolls horizontally; all four workspace tabs remain visible.

Contrast a schedule finding: it affects schedule assurance and carries no invented dollar impact. The displayed control severity index is a severity heuristic, not a probability.

## 2:45–3:45 — Show what changes the gate

Return to **Showcase examples** and run **2. Forecast reconciled**. Its supplied cost fields now reconcile; the forecast gap is zero. The gate still reads **REVIEW REQUIRED**, with two schedule findings.

Run **3. Selected controls satisfied**. Its supplied cost and schedule fields satisfy all 32 applicable checks. One activity check remains not applicable because the activity is not started.

These cases are constructed input snapshots. The engine did not correct the records or authorize the changes. This is not a demonstration of cross-period comparison.

## 3:45–4:30 — Demonstrate the configurable control

Open **Controls & coverage**, expand **Inspect a control result**, select **Passed** and choose a `portfolio.board_authorization` result. **Inspect selected result** shows the exact EAC and authorization limit used by the equation:

```text
EAC <= delegated_authorization
```

Each case supplies synthetic authorization limits for all three accounts, so the custom rule actually executes and passes. The input values illustrate a declared threshold; they are not evidence of real management approval.

Switch **Result status** to **Not applicable** to inspect the activity check that did not run. These recorded results are distinct from the catalogue and equation editor below, which configure the next file analysis. Editing a draft does not change the active result.

Catalogue and custom equations use a restricted expression evaluator; imported code, attribute access, assignments and undeclared fields are rejected.

## 4:30–5:00 — Leave something inspectable

Download the **executive brief** and **Export analysis JSON**. The brief gives the gate and findings; the JSON retains source hashes, per-record findings, equation definitions and applicability results. Expand **Workspace options** to reopen a JSON analysis, reset the demo or manage browser storage. Keep the original source files alongside the JSON; it does not preserve every source field.

Explain the operating boundary:

- The hosted workbench can analyze user-selected CSV, P6 XER and equation files directly in the browser; it does not upload them to a server.
- It is session-only by default. **Remember workspace on this browser** explicitly opts into browser storage.
- `eq-controls serve` uses the Python engine on loopback and request-scoped temporary uploads.
- The CLI writes its four output files to the specified local directory.
- `CLOSE READY` means no selected, applicable control failed. It is not completeness certification or approval.

## Presenter checks

Before a meeting, open each case once and confirm its expected gate. Use the [generated reports](SHOWCASE.md#inspect-the-outputs-without-installing-anything) as an offline fallback. The [fixture guide](../examples/close_walkthrough/README.md) records every input change and the expected CLI exit codes.

The built-in **Take the 90-second tour** is a six-step walkthrough of whichever result is active. Its guide appears above the relevant evidence and ends with control coverage and a brief download. **Open workspace** scrolls to the active analysis without replacing it. The original hyperscale demo remains available through **Workspace options → Reset to demo**.
