# Contributing

Contributions should preserve the project's central properties: every proof claim must be independently reproducible from the artifact, and every project-controls claim must remain bounded by the declared source fields, equations and runtime mode.

## Opening an issue

Use the structured GitHub issue forms:

- **Bug report** for reproducible defects using the smallest synthetic or sanitized fixture possible.
- **Feature request** for a bounded capability with an explicit decision, evidence plan, trust boundary and non-claims.

Do not file vulnerabilities, exploit details, private project data, credentials, private keys or sensitive proof artifacts in a public issue. Use GitHub's private security-advisory interface instead. Review `docs/RUNTIME_MODES.md`, `docs/SEMANTIC_MODEL.md`, the current roadmap and open issues before filing.

## Before opening a change

Install the Python development environment and run the repository proof:

```bash
python -m pip install -e '.[dev]'
python scripts/check_repository.py
```

For browser, interface, runtime-boundary or JavaScript changes, also run:

```bash
npm ci
npm run test:browser-engine
npm run test:ui
```

`test:browser-engine` includes the shared-fixture semantic comparison between the browser engine and the Python-generated public Control Room artifact.

## Expectations

- Keep both expression languages deliberately small; explain every grammar expansion.
- Add adversarial tests for parser, proof, signature, replay and browser-equation changes.
- Do not weaken fail-closed behaviour to make an example pass.
- Update JSON Schemas and documentation with contract changes.
- Add an ADR for algorithm, proof-format or trust-boundary changes.
- Do not commit private keys, generated output directories or machine-specific secrets.
- Keep the hosted browser, loopback application and CLI boundaries aligned with `docs/RUNTIME_MODES.md`.
- Add or update automated contract tests whenever file movement, browser persistence, temporary-file handling, telemetry or outbound-network behaviour changes.
- Preserve the distinction between the compatibility field `defensible_eac` and the visitor-facing label **detail-reconstructed EAC**.
- Treat the combined control severity index as a non-calibrated triage heuristic; do not describe it as a probability or assurance percentage.

## Commit quality

Prefer small commits that each leave the repository executable. Commit messages should describe the engineering outcome rather than the editing action.

## Review checklist

A reviewer should be able to answer:

1. What invariant changes?
2. What new failure mode is introduced?
3. Which test proves the intended behaviour?
4. Can old proof and Control Room artifacts still be interpreted safely?
5. Do the Python and browser implementations still produce the same decision semantics for shared fixtures?
6. Does any README, security or runtime claim outrun the checked-in evidence?
7. Does the change retain project data longer or move it across a new boundary?
