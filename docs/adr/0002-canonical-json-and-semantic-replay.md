# ADR 0002: Canonical JSON, Ed25519, and semantic replay

- Status: Accepted
- Date: 2026-07-13

## Context

A signature proves that bytes were signed. It does not prove that a signed numerical claim is feasible or minimal. The project needs a portable artifact that can be inspected without a service dependency.

## Decision

- Preserve the complete specification, submission, result, diagnostics, and engine parameters in JSON.
- Canonicalize the proof core with sorted compact JSON and prohibit non-finite values.
- Hash with SHA-256.
- Support optional Ed25519 signatures.
- Make semantic replay the default verification path.

## Consequences

- Proofs are self-contained and offline-verifiable.
- A malicious signer cannot make a false repair pass full verification merely by signing it.
- Embedded public keys establish possession, not identity; trusted key distribution remains external.
- Proof schema and algorithm identifiers become compatibility-critical contracts.
