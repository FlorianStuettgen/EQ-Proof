# Security policy

Please report security issues privately through GitHub's security advisory interface rather than a public issue.

## Supported version

| Version | Supported |
| --- | --- |
| 1.x | Yes |
| < 1.0 | No |

## Key handling

EQ-Proof never needs network access. Keep private keys outside the repository, restrict filesystem permissions, and supply trusted public-key fingerprints through a separate channel. The checked-in evidence key is explicitly a deterministic demonstration key and must never be used for real identity or authorization.

## Security boundary

A valid proof establishes integrity of the encoded artifact and, in Ed25519 mode, possession of the matching private key. It does not establish that the constraints are correct, that the input was truthful, or that the signer is who they claim to be without an independently trusted key fingerprint.
