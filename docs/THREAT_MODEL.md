# Threat model

## Assets

- integrity of the encoded specification and submission;
- correctness of the claimed repair under the supported algorithm;
- confidentiality and control of private signing keys;
- stable interpretation of versioned proof artifacts.

## Adversaries considered

1. A transport or storage actor modifies a proof after creation.
2. An actor substitutes a different public key and signature.
3. A signer knowingly signs a numerically false result.
4. A specification author attempts to inject executable Python syntax.
5. An input supplies missing, extra, non-numeric, NaN, or infinite values.
6. A malformed or oversized expression attempts to consume unreasonable parser resources.

## Controls

| Threat | Control |
| --- | --- |
| Payload mutation | Canonical SHA-256 |
| Key/signature substitution | Separately trusted public-key match |
| Validly signed false result | Semantic replay |
| Code execution through equations | Allow-listed AST compiler; no `eval` |
| Shape/numeric confusion | Exact variable-set and finite-number validation |
| Parser abuse | Expression-length and AST-node limits |
| Partial output writes | Atomic CLI and key writes |
| Private-key exposure in repository | `.gitignore`, POSIX `0600`, explicit documentation |

## Explicit exclusions

EQ-Proof does not protect against:

- a malicious or incorrect business specification;
- falsified upstream source data;
- compromise of the host running verification;
- side-channel leakage from the cryptographic library;
- denial of service within configured but expensive numerical inputs;
- identity claims without an external trust system;
- unsupported nonlinear or integer problems.

## Demonstration key

The checked-in evidence public key is derived from a deterministic private seed used only inside the regeneration script. It is intentionally non-secret and must never be used for authentication, authorization, or real provenance.
