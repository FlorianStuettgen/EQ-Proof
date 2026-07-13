# Security policy

## Reporting

Please report suspected vulnerabilities privately through GitHub's security advisory interface. Do not open a public issue containing exploit details, private keys, or sensitive proof artifacts.

## Supported versions

| Version | Supported |
| --- | --- |
| 1.1.x | Yes |
| 1.0.x | Security fixes only |
| < 1.0 | No |

## Security properties

Full verification checks three distinct properties:

1. canonical payload integrity through SHA-256;
2. optional Ed25519 signature validity and trusted-key matching;
3. semantic replay of the encoded specification, submission, result, movement, objective, and diagnostics.

A signature alone is not treated as proof of numerical correctness.

## Key handling

- Keep private keys outside the repository and normal output directories.
- Restrict filesystem access; generated private keys use mode `0600` on POSIX systems.
- Distribute trusted public keys or fingerprints through an independent channel.
- Rotate keys according to the surrounding organization's policy.
- Never use the deterministic demonstration key for real authentication, authorization, or provenance.

EQ-Proof is not a key-management service and does not provide HSM, KMS, certificate, revocation, or organizational identity infrastructure.

## Runtime boundary

The package requires no network access. Equations are parsed through an allow-listed AST compiler and are never evaluated as Python. Unsupported, nonlinear, executable, oversized, and ambiguous syntax fails closed.

See [Threat model](docs/THREAT_MODEL.md) for assets, adversaries, controls, and exclusions.
