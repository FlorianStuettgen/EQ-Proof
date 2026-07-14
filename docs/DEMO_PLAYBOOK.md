# EQ-Proof Control Room Demo Playbook

This is the five-minute walkthrough for a project-controls leader, data-platform reviewer, or engineering panel.

## Demo objective

Do not begin with the equation engine. Begin with the decision:

> Is this monthly close internally consistent, which parts of the position can be defended from governed components, and what requires escalation before reporting?

Use the checked-in synthetic hyperscale data-centre close. It is deliberately inconsistent while each individual value remains superficially plausible.

## 0:00–0:30 — Establish the operating problem

Open the application and state:

> Project teams usually validate P6, cost, change and risk in separate tools. EQ-Proof compiles those exports into one equation-backed evidence model before the close is signed.

Point out that the public demo is synthetic. Real files are processed by the loopback-only local application with no telemetry.

## 0:30–1:20 — Show the executive gate

Start on **Explain the surprise**.

The demo displays:

- reported EAC: **$407M**;
- defensible EAC from `AC + ETC`: **$418M**;
- deterministic forecast gap: **$11M**;
- reconstructed risk-adjusted position: **$483M**;
- submitted risk-adjusted summary: **$472M**;
- risk-adjusted reconciliation gap: **$11M**;
- exposure above reported EAC: **$76M**;
- close decision: **CLOSE BLOCKED**.

Explain the logical separation:

1. the submitted deterministic forecast is $407M;
2. governed `AC + ETC` reconstructs to $418M, exposing $11M of deterministic contradiction;
3. declared pending change and configured risk uplift total $65M;
4. adding that declared exposure to defensible EAC produces a $483M risk-adjusted bridge;
5. the submitted risk-adjusted summary is $472M, so it is also $11M below the reconstructed bridge;
6. the full risk-adjusted position is $76M above reported deterministic EAC, but only $11M of that is an arithmetic forecast contradiction.

Do not call the bridge a calculated P80. EQ-Proof validates supplied relationships; it does not run a probabilistic risk simulation.

Click `MEP-200`. Show its $37M position above reported EAC as three separately labelled components: $7M deterministic contradiction, $12M pending change and $18M configured risk uplift.

## 1:20–2:20 — Trace declared evidence

Open **Evidence graph**.

Explain the graph from left to right:

```text
source record → violated equation → declared metric or assurance domain → close gate
```

Click a cost blocker. The inspector shows:

- source record;
- equation ID and expression;
- residual;
- deterministic forecast impact;
- prescribed remediation.

Then click a schedule finding. Show that it routes to **schedule assurance**, not a dollar value. This is a deliberate credibility boundary: EQ-Proof does not invent financial causality from negative float or remaining-duration defects.

## 2:20–3:00 — Operate the exception register

Open **Exception command centre**.

Demonstrate:

- severity, domain and text filters;
- ranking by severity and materiality;
- the EAC identity blocker;
- the unauthorized budget bridge;
- spreadsheet-safe CSV export.

Explain that the register can move into Excel, Power Query, Power BI, Smartsheet, SharePoint or ticket automation.

## 3:00–4:00 — Demonstrate equation extensibility

Open **Equation workbench**.

Show the tested catalogue across cost, earned value, change, risk and P6 schedule assurance.

Add:

```text
EAC <= delegated_authorization
```

with required fields:

```text
EAC, delegated_authorization
```

In local mode, **Validate and add** sends the equation to the same server-side parser used during analysis. In public-demo mode, the equation can be assembled and downloaded as a pack, but private-file execution remains disabled.

Emphasize that catalogue and user-authored controls share the same restricted evaluator. Arbitrary Python execution, imports, attributes, assignment, undeclared fields, duplicate IDs and unsupported syntax are rejected.

## 4:00–4:40 — Show the real-file workflow

Choose **Analyze your close**.

The local app accepts:

- one or more Primavera P6 XER exports;
- one or more generic cost/control-account CSV exports;
- optional equation-pack JSON files;
- equations authored in the browser;
- an explicit three-letter currency label.

Clarify the adapter boundary:

- P6 support is native for XER `TASK` records;
- cost-system support is deterministic CSV alias mapping, not a live EcoSys, SAP, Oracle or Cobra connector.

The application hashes source files, runs only applicable equations, embeds the equation manifest and returns the same decision cockpit.

## 4:40–5:00 — Close on the technical boundary

State clearly:

- the hosted demo uses synthetic data only;
- real-file analysis runs through `eq-controls serve` on loopback;
- uploads live only in a request-scoped operating-system temporary directory;
- file, request, equation and row limits bound local resource use;
- there is no telemetry, CDN or external model call;
- the CLI can emit `analysis.json`, `control-room.json`, `exceptions.csv` and `report.md` for monthly-close automation;
- the independently versioned lower proof engine can attest and semantically replay supported numerical repairs.

End with:

> EQ-Proof does not replace P6, the cost system, risk modelling or governance. It makes declared relationships executable, traceable and difficult to hand-wave away.
