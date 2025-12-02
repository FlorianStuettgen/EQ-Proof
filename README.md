
#Equation-Governed Output Repair & Attestation (Offline)

EQ-PROOF validates and **repairs** numeric outputs against a JSON spec of constraints (bounds, equalities, simplex, monotonicity, sum≤cap), then emits a signed proof artifact (JSON/MD/PDF). Runs **offline** by default (network disabled).

## Quickstart
```bash
python -m venv .venv && . .venv/bin/activate
pip install sympy numpy matplotlib  # add pynacl for Ed25519, openpyxl for XLSX
# Budget demo
python cli.py examples/spec_budget_cap.json examples/inputs_budget_bad.json --out outputs/proof_budget.json --md outputs/proof_budget.md --pdf outputs/proof_budget.pdf
# Verify (auto tries Ed25519 then HMAC)
python verify_cli.py outputs/proof_budget.json
```

## Features
- Constraints: **bounds**, **equality** (symbolic solve then numeric fallback), **sum≤cap**, **simplex**, **monotone**.
- Units/dimensions: canonical units in spec; inputs can be `{value, unit}` and will be converted.
- Attestation: **Ed25519** (if `pynacl` + key present) or **HMAC-SHA256** fallback.
- Reports: Markdown + optional PDF (matplotlib).
- Tools: CLI, verifier, spreadsheet CSV bridge, debug notebook.
- Offline by default (`eq_proof.no_net` denies outbound sockets).

See `docs/` for details and `examples/` for ready specs. Prebuilt artifacts live in `outputs/`.
