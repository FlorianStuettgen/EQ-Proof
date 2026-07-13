# Project Controls Equation Workbench

## What it solves

The workbench applies a tested project-controls equation catalogue and user-authored equation packs directly to Primavera P6 XER and cost/control-account CSV exports.

It is intended to replace copied monthly QA formulas with a repeatable close gate.

## Run the example

```bash
eq-controls analyze \
  --p6-xer examples/hyperscale_close/schedule.xer \
  --cost-csv examples/hyperscale_close/cost.csv \
  --output outputs/hyperscale-close
```

The example intentionally exits `3` because blocker findings are present.

## Outputs

- `analysis.json` for automation and audit;
- `exceptions.csv` for Excel, Power Query, Power BI or workflow tools;
- `report.md` for the close-review record.

## Equation catalogue

```bash
eq-controls catalogue
eq-controls catalogue --json
```

The catalogue spans cost, EVM, change, risk and schedule checks. Equations execute only when their required fields are available.

## User equation packs

```json
[
  {
    "id": "governance.authorization",
    "title": "EAC remains inside delegated authority",
    "domain": "governance",
    "expression": "EAC <= delegated_authorization",
    "severity": "blocker",
    "required_fields": ["EAC", "delegated_authorization"]
  }
]
```

```bash
eq-controls analyze \
  --cost-csv close.csv \
  --equations governance.json \
  --output outputs/close
```

## P6 boundary

The native adapter currently reads the XER `TASK` table. It does not require P6 database access or API credentials. Current canonical fields include activity ID, WBS, status, original duration, remaining duration, total float and physical progress.

## Operating model

1. Export XER and cost data using the ordinary monthly process.
2. Run one command.
3. Treat exit `3` as a blocked close.
4. Assign and resolve the ranked exception register.
5. Rerun until the close gate passes.
6. Retain the JSON result with the reporting-cycle evidence.

The engine does not approve changes or determine contractual truth. It ensures that the supplied controls state is consistent with the tested and user-supplied equations.
