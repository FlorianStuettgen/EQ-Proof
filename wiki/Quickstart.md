# Quickstart

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

Diagnose:

```bash
eq-proof validate --spec examples/portfolio_allocation/spec.json --input examples/portfolio_allocation/input.json
```

Repair:

```bash
eq-proof repair \
  --spec examples/portfolio_allocation/spec.json \
  --input examples/portfolio_allocation/input.json \
  --proof outputs/proof.json \
  --report outputs/report.md
```

Verify with semantic replay:

```bash
eq-proof verify outputs/proof.json
```

For signer identity, generate a keypair, sign with `--private-key`, and verify with a separately trusted `--public-key`.
