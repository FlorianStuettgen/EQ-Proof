# Spreadsheet Bridge

`bridges/spreadsheet_bridge.py` reads a CSV with these headers:

```csv
variable,value,unit
x1,60,
x2,50,
x3,40,
cap,120,
```

Run it from the repository root:

```bash
.venv\Scripts\python.exe bridges\spreadsheet_bridge.py examples\spec_budget_cap.json inputs.csv --out-csv outputs\repaired.csv
```

The bridge writes a repaired CSV, a proof JSON file, and a Markdown proof report.
