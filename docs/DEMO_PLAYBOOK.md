# EQ-Proof Control Room Demo Playbook

This is the five-minute product walkthrough for a project-controls leader, data-platform reviewer, or engineering panel.

## Demo objective

Do not begin with the equation engine. Begin with the decision the user must make:

> Is this monthly close safe to report, and what is being hidden by the submitted summaries?

Use the checked-in synthetic hyperscale data-centre close. It is deliberately internally inconsistent while every individual number remains superficially plausible.

## 0:00–0:30 — Establish the operating problem

Open the application and state:

> Project teams usually validate P6, cost, change, and risk in separate tools. EQ-Proof compiles those exports into one equation-backed evidence model before the close is signed.

Point out that the public demo is synthetic. Real files are processed by the local application with no telemetry.

## 0:30–1:15 — Show the executive gate

Start on **Explain the surprise**.

The demo should display:

- reported EAC: **$407M**;
- defensible EAC: **$418M**;
- defensible P80: **$483M**;
- hidden exposure: **$76M**;
- close decision: **CLOSE BLOCKED**.

Explain the reconstruction:

1. the submitted deterministic forecast is $407M;
2. governed `AC + ETC` reconstructs to $418M, exposing $11M of forecast contradiction;
3. pending change and quantified risk add another $65M;
4. the defensible risk-adjusted position is therefore $483M;
5. $76M is not visible in the reported EAC.

Click `MEP-200`. Show that its $37M contribution consists of a $7M forecast contradiction, $12M pending change, and $18M quantified risk.

## 1:15–2:15 — Trace the evidence

Open **Evidence graph**.

Explain the graph from left to right:

```text
source record → violated equation → reconstructed metric → close decision
```

Click a blocker node. The inspector must show:

- source record;
- equation ID and expression;
- residual;
- executive metric affected;
- prescribed remediation.

The point is not a decorative dependency graph. It is navigable controls lineage: every headline number can be traced back to the source evidence and rule that produced it.

## 2:15–3:00 — Operate the exception register

Open **Exception command centre**.

Show that failures are ranked by severity and materiality rather than source-file order. Open the EAC identity failure and the unauthorized budget bridge.

Export the CSV and explain that the register can move directly into Excel, Power Query, Power BI, Smartsheet, SharePoint, or ticket automation.

## 3:00–4:00 — Demonstrate equation extensibility

Open **Equation workbench**.

Show the tested catalogue across cost, earned value, change, risk, and P6 schedule health.

Add the supplied example:

```text
EAC <= delegated_authorization
```

Required fields:

```text
EAC, delegated_authorization
```

Emphasize that catalogue and user-authored controls run through the same safe expression evaluator. Arbitrary Python execution, imports, attributes, and unsupported syntax are rejected.

## 4:00–4:40 — Show real-file workflow

Choose **Analyze your close**.

The local app accepts:

- one or more Primavera P6 XER exports;
- one or more cost/control-account CSV exports;
- optional equation-pack JSON files;
- equations authored in the browser.

The application automatically maps common project-controls aliases, runs only equations whose required fields are available, and returns the same decision cockpit.

## 4:40–5:00 — Close on the technical boundary

State clearly:

- the static hosted demo uses synthetic data;
- real-file analysis runs locally through `eq-controls serve`;
- uploads are held only in an operating-system temporary directory for the request;
- there is no telemetry or external model call;
- the CLI remains available for CI and monthly-close automation;
- the lower proof engine can attest and semantically replay supported numerical repairs.

End with:

> EQ-Proof does not replace P6, the cost system, or governance. It makes the relationships among them executable, reviewable, and difficult to hand-wave away.
