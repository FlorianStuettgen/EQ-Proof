# Development

Run the complete repository proof:

```bash
python scripts/check_repository.py
```

Regenerate deterministic evidence:

```bash
python scripts/regenerate_evidence.py
git diff --exit-code
```

Inspect the local scaling baseline:

```bash
python scripts/benchmark_solver.py
```

Contract changes require schema updates, compatibility analysis, adversarial tests, and documentation. Algorithm or trust-boundary changes require an ADR.
