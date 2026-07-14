## Purpose

Describe the problem, the product boundary, and why this change belongs in EQ-Proof.

## Evidence and semantic integrity

- [ ] Claims are limited to what the supplied fields and equations actually prove.
- [ ] Deterministic, risk-adjusted, causal, and probabilistic conclusions remain clearly separated.
- [ ] Source hashes, equation manifests, schema versions, and replayability remain intact where applicable.
- [ ] Generated evidence was regenerated and checked for drift.

## Product and UI boundary

- [ ] The audited Control Room shell is reused rather than cosmetically redesigned.
- [ ] Any UI change is tied to a functional requirement or a reproducible audit finding.
- [ ] Keyboard, focus, mobile, reduced-motion, empty-state, and export behavior remain coherent.
- [ ] Public demo mode and loopback local-file mode remain honestly distinguished.

## Validation

- [ ] `repository-proof` passes.
- [ ] `ui-audit` passes for changes affecting the web product or browser behavior.
- [ ] `CodeQL` passes.
- [ ] Pages bundle validation passes for hosted-product changes.
- [ ] The production deployment is verified after merge when Pages assets change.

## Compatibility and operations

- [ ] Existing schemas and CLI behavior remain backward compatible, or the migration is explicit.
- [ ] No secrets, telemetry, or external runtime dependencies were introduced unintentionally.
- [ ] Documentation and release notes match the implementation.
