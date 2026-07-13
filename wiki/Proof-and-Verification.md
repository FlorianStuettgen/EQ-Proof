# Proof and verification

## Integrity

SHA-256 covers a canonical JSON representation of every proof field except the attestation itself.

## Authenticity

Ed25519 proves possession of the matching private key. A separate trusted public key is required to bind that key to an expected identity.

## Semantic correctness

The verifier re-parses the embedded specification, reruns the projection, and compares the result, movement, objective, residuals, and diagnostics.

## Modes

- default — integrity, optional signature, and semantic replay;
- `--integrity-only` — skips replay and reports that fact;
- digest-only proof — no signer identity claim, but replay still runs by default.
