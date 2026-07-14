# Proof format

The authoritative output is JSON conforming to [`schemas/proof.schema.json`](../schemas/proof.schema.json).

## Top-level sections

| Section | Contents |
| --- | --- |
| `proof_schema` | Artifact contract identifier |
| `created_utc` | Creation timestamp |
| `engine` | Version, algorithm ID, tolerance, iteration budget, actual cycles |
| `specification` | Name, schema version, digest, full source document |
| `submission` | Digest and exact submitted values |
| `result` | Status, repaired values, movement, objective, residuals |
| `diagnostics` | Constraint checks before and after repair |
| `attestation` | Digest-only or Ed25519 material |

## Canonical payload

The attestation covers every top-level field except `attestation` itself. The remaining object is serialized as UTF-8 JSON with:

- keys sorted recursively;
- no insignificant whitespace;
- non-ASCII characters preserved;
- NaN and infinities prohibited.

The SHA-256 of those bytes is stored as `attestation.payload_sha256`.

## Computed-number normalization

Submitted values and the source specification are preserved exactly as parsed because they are source claims.

Computed proof outputs are normalized to **15 significant decimal digits** before hashing and signing:

- repaired values;
- Euclidean movement and objective;
- maximum violations;
- diagnostic left-hand sides, right-hand sides and violations.

IEEE-754 subnormal zero noise is canonicalized to `0.0`. This removes platform-specific one-ULP representation drift while retaining materially more precision than the verifier's declared comparison tolerance.

The numerical algorithm remains `dykstra-l2-v1`; engine version `1.4.0` records the serialization-stability fix. Existing `proof@1` artifacts remain verifiable because semantic replay compares claimed values to independently recomputed values within the declared tolerance.

## Digest-only mode

Digest-only mode supports mutation detection only when the expected digest is obtained from a trusted channel. Because an attacker can modify a payload and recompute its digest, it provides no origin claim.

EQ-Proof still performs semantic replay in this mode by default. The verifier distinguishes numerical correctness from signer identity.

## Ed25519 mode

The attestation embeds:

- the raw public key;
- the signature over canonical payload bytes;
- a SHA-256 fingerprint of the encoded public key;
- an explicit trust note.

Verification with only the embedded key proves internal signature consistency. Verification with `--public-key` additionally requires the embedded key to match a separately supplied trusted key.

## Semantic claims

The verifier independently recomputes:

- specification and submission digests;
- the repaired vector;
- Euclidean movement and objective value;
- maximum violations before and after;
- every diagnostic row.

The proof does not contain a general mathematical certificate for arbitrary solvers. It contains enough data for deterministic replay of the supported algorithm contract.
