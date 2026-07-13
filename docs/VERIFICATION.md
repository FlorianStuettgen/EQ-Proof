# Verification

## Default verification

```bash
eq-proof verify proof.json --public-key trusted-public.pem
```

Success means:

```text
VERIFIED integrity=pass signature=pass semantics=pass fingerprint=<sha256>
```

## Layer 1: integrity

The verifier removes the attestation object, canonicalizes the remaining payload, and recomputes SHA-256. Any changed specification, input, result, diagnostic, timestamp, or engine parameter invalidates the digest.

## Layer 2: authenticity

For Ed25519 proofs, the verifier checks the signature against the embedded key. When a trusted public key is supplied, the verifier also requires an exact key match. This prevents an attacker from replacing both the payload and embedded key.

A key fingerprint must still be distributed through an independent trust channel. Cryptography cannot establish organizational identity on its own.

## Layer 3: semantic replay

The verifier treats the proof's numerical claims as untrusted input. It re-parses the specification and reruns the algorithm with the encoded parameters. It rejects mismatches in:

- result status;
- variable set;
- repaired values;
- Euclidean movement;
- objective value;
- pre/post maximum residuals;
- diagnostic IDs, rules, relations, residuals, and satisfaction flags.

This catches a validly signed false result.

## Integrity-only mode

```bash
eq-proof verify proof.json --integrity-only
```

This skips semantic replay and prints `semantics=skipped`. It is intended for rapid transport checks, not final acceptance.

## Exit behaviour

- `0` — requested verification layers passed;
- `2` — malformed artifact, digest mismatch, signature failure, key mismatch, unsupported algorithm, or semantic mismatch.

## Compatibility

Unknown proof schemas and algorithm IDs fail closed. A verifier must not silently reinterpret a proof generated under a different numerical contract.
