# Security

EQ-PROOF is offline by default. Importing the package installs a socket guard that blocks outbound connections unless `EQPROOF_ALLOW_NET=1` or `EQPROOF_ALLOW_NET=true` is set.

Proofs are signed locally:

- Ed25519 is used when PyNaCl is installed and `keys/ed25519_sk.hex` exists.
- HMAC-SHA256 is used as a fallback with `EQPROOF_KEY`, `keys/attest_key.txt`, or the built-in demo key.

The demo key is for reproducible examples only. Use Ed25519 or a private HMAC key for real attestations.

The `keys/` directory ignores real key files. Do not commit production secrets.
