# Contributing

Contributions should preserve the project's central property: every claim in a proof must be independently reproducible from the artifact.

## Before opening a change

```bash
python -m pip install -e '.[dev]'
python scripts/check_repository.py
```

## Expectations

- Keep the expression language deliberately small; explain every grammar expansion.
- Add adversarial tests for parser, proof, signature, and replay changes.
- Do not weaken fail-closed behaviour to make an example pass.
- Update JSON Schemas and documentation with contract changes.
- Add an ADR for algorithm, proof-format, or trust-boundary changes.
- Do not commit private keys, generated output directories, or machine-specific secrets.

## Commit quality

Prefer small commits that each leave the repository executable. Commit messages should describe the engineering outcome rather than the editing action.

## Review checklist

A reviewer should be able to answer:

1. What invariant changes?
2. What new failure mode is introduced?
3. Which test proves the intended behaviour?
4. Can old proof artifacts still be interpreted safely?
5. Does any README claim outrun the checked-in evidence?
