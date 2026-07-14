# Project Controls Equation Workbench

## What it solves

The workbench applies a tested project-controls equation catalogue and user-authored equation packs directly to Primavera P6 XER and generic cost/control-account CSV exports.

It replaces copied monthly QA formulas with a repeatable close gate and a traceable reconstruction of declared project-controls states.

## Run the example

```bash
eq-controls analyze \
  --p6-xer examples/hyperscale_close/schedule.xer \
  --cost-csv examples/hyperscale_close/cost.csv \
  --equations examples/hyperscale_close/custom_equations.json \
  --currency USD \
  --output outputs/hyperscale-close
```

The example exits `3` because blocker findings are present.

## Outputs

- `analysis.json` — source hashes, executed equation manifest and all results;
- `control-room.json` — schema-versioned executive reconstruction and evidence graph;
- `exceptions.csv` — spreadsheet-safe action register;
- `report.md` — close-review record.

## Reconstructed states

EQ-Proof keeps these concepts separate:

```text
reported EAC                    = submitted EAC
defensible EAC                  = AC + ETC
deterministic forecast gap      = defensible EAC - reported EAC
reconstructed risk-adjusted EAC = defensible EAC + pending change + configured risk uplift
risk-adjusted reconciliation    = reconstructed risk-adjusted EAC - submitted risk-adjusted EAC
```

The bridge is not a statistical P80 calculation. See the [Semantic Model](https://github.com/FlorianStuettgen/EQ-Proof/blob/main/docs/SEMANTIC_MODEL.md).

## Equation catalogue

```bash
eq-controls catalogue
eq-controls catalogue --json
```

The catalogue spans cost, earned value, change, risk and schedule assurance. Equations execute only when their required fields are available and any optional applicability predicate matches.

## User equation packs

```json
[
  {
    "id": "governance.authorization",
    "title": "EAC remains inside delegated authority",
    "domain": "governance",
    "expression": "EAC <= delegated_authorization",
    "severity": "blocker",
    "required_fields": ["EAC", "delegated_authorization"],
    "record_type": "control_account"
  }
]
```

```bash
eq-controls analyze \
  --cost-csv close.csv \
  --equations governance.json \
  --fail-on blocker \
  --output outputs/close
```

## P6 and cost boundaries

The native P6 adapter currently reads the XER `TASK` table. It does not require P6 database access or API credentials. Canonical fields include activity ID, WBS, status, original duration, remaining duration, total float and physical progress.

Cost-system support is deterministic alias mapping over exported CSV tables. It is not a live EcoSys, SAP, Oracle or Cobra connector.

## Operating model

1. Export XER and cost data using the ordinary monthly process.
2. Select catalogue controls and add project-specific equations.
3. Compile the close locally or through the CLI.
4. Treat blocker failures as a blocked close; optionally use `--fail-on` for a stricter automation threshold.
5. Assign and resolve the ranked exception register.
6. Rerun until the selected gate is clear.
7. Retain the source hashes, equation manifest and JSON outputs with the reporting-cycle evidence.

The engine does not approve changes, calculate probabilistic risk, or determine contractual truth. It evaluates whether the supplied controls state is internally consistent with the declared equations.
