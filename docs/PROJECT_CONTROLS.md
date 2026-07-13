# Project Controls Equation Workbench

## Purpose

The workbench converts ordinary project-controls exports into an automated assurance gate. It is designed for the recurring problem where cost, schedule, earned-value, change and risk numbers are individually plausible but mutually inconsistent.

The operator supplies:

- one or more Primavera P6 XER exports;
- one or more cost or control-account CSV exports;
- optional JSON equation packs written by the user.

The workbench automatically maps common field names, selects catalogue equations whose required fields are available, evaluates the equations record by record, ranks failures and emits a close package.

## One-command close gate

```bash
eq-controls analyze \
  --p6-xer examples/hyperscale_close/schedule.xer \
  --cost-csv examples/hyperscale_close/cost.csv \
  --output outputs/hyperscale-close
```

Exit codes are operational:

| Code | Meaning |
| ---: | --- |
| `0` | no blocker findings; close gate passed |
| `2` | invalid input, equation pack or execution error |
| `3` | blocker findings; close gate failed |

Outputs:

- `analysis.json` — full machine-readable result;
- `exceptions.csv` — ranked action register for Excel, Power BI or workflow ingestion;
- `report.md` — human-readable close decision record.

## Tested equation catalogue

The built-in catalogue currently covers:

- `EAC = AC + ETC`;
- `VAC = BAC - EAC`;
- `CV = EV - AC`;
- `SV = EV - PV`;
- `CPI = EV / AC`;
- `SPI = EV / PV`;
- current budget bridge to baseline plus approved change;
- P80 bridge to deterministic EAC, pending change and quantified risk;
- P6 in-progress activities with zero remaining duration;
- extreme negative total float.

Catalogue equations are deliberately explicit. Each one carries required fields, tolerance, severity, explanation and prescribed remediation.

## User equations

User equation packs are JSON arrays:

```json
[
  {
    "id": "portfolio.board_authorization",
    "title": "EAC remains inside delegated authorization",
    "domain": "governance",
    "expression": "EAC <= delegated_authorization",
    "severity": "blocker",
    "description": "Forecasts beyond delegated authority require escalation.",
    "remediation": "Supply approved authority or escalate the forecast.",
    "required_fields": ["EAC", "delegated_authorization"]
  }
]
```

Supported syntax includes numeric constants, supplied fields, parentheses, `+`, `-`, `*`, `/`, comparisons and the allow-listed functions `abs`, `min`, `max` and `round`. Python imports, attributes and arbitrary execution are rejected.

## Native tool integration

### Primavera P6

The XER adapter reads the P6 `TASK` table directly and maps activity ID, WBS, status, original and remaining duration, total float and physical progress into canonical fields. No P6 database connection or API credential is required.

### Cost systems and spreadsheets

CSV ingestion recognizes common aliases such as `budget_at_completion`, `actual_cost`, `estimate_to_complete`, `forecast_at_completion`, `BCWS` and `BCWP`. Source-specific exports can therefore be checked without first rebuilding them into a bespoke template.

### Downstream use

`exceptions.csv` is intentionally flat and stable so it can be loaded directly into Excel, Power Query, Power BI, Smartsheet, SharePoint lists or an issue-management workflow.

## Why this is useful

Most controls QA happens through manually maintained spreadsheet checks that are difficult to reuse, version, test or audit. The workbench turns those checks into portable equation packs and combines them with a tested catalogue. The same close logic can therefore run against every reporting cycle and every project without copying formulas between workbooks.

The result is not another dashboard. It is an executable, versionable acceptance gate for the data feeding the dashboard.
