# Security model

EQ-Proof protects artifact integrity, optional signer possession, and numerical consistency under the supported specification.

It does not prove that the rules are wise, the source data is truthful, or a public key belongs to an organization without an external trust channel.

The equation compiler is allow-listed and does not use `eval`. Private keys are excluded from Git and generated with restrictive permissions on POSIX systems.

See `SECURITY.md` and `docs/THREAT_MODEL.md`.
