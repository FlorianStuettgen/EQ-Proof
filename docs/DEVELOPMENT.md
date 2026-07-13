# Development

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Repository proof

```bash
python scripts/check_repository.py
```

This runs tests with branch coverage, compiles all package modules, regenerates deterministic evidence, and—inside a Git checkout—requires a clean diff.

## Targeted commands

```bash
pytest tests/test_compiler.py
pytest tests/test_proof.py -k semantic
python -m compileall -q src
python scripts/regenerate_evidence.py
git diff --exit-code
python scripts/benchmark_solver.py
```

## Change discipline

- Any proof-format change requires a schema and compatibility decision.
- Any algorithm change requires a new algorithm identifier or evidence that replay semantics are unchanged.
- Any supported grammar change requires compiler security tests.
- Any README numerical claim must be generated or directly traceable to checked-in evidence.
- Coverage must remain at or above the configured gate; the absolute percentage is not a substitute for adversarial tests.

## Release checklist

1. Update package version and changelog.
2. Run `python scripts/check_repository.py`.
3. Regenerate the benchmark only when methodology or relevant code changes.
4. Inspect the proof diff; deterministic evidence should change only for intentional contract changes.
5. Build a wheel with `python -m pip wheel . --no-deps -w dist`.
6. Tag only after the main-branch checks pass.
