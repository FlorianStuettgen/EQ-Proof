# EQ-Proof Repair Report

## Decision record

| Field | Value |
| --- | --- |
| Specification | `portfolio-allocation` |
| Status | `repaired` |
| Euclidean movement | `0.0707106781187` |
| Objective value | `0.0025` |
| Maximum violation before | `0.1` |
| Maximum violation after | `0` |
| Algorithm | `dykstra-l2-v1` |
| Iterations | `2` |
| Attestation | `Ed25519` |
| Signer fingerprint | `aab09c9a9e2586699021cba3d7e7d1e6300267e90c922b07fdd9eb3081199148` |

## Values

| Variable | Submitted | Repaired | Delta |
| --- | ---: | ---: | ---: |
| `forecast_a` | 0.55 | 0.5 | -0.05 |
| `forecast_b` | 0.35 | 0.3 | -0.05 |
| `forecast_c` | 0.2 | 0.2 | 0 |

## Violations detected before repair

- `allocation-total`: violation `0.1` — `forecast_a + forecast_b + forecast_c == 1`

## Verification boundary

The JSON proof is authoritative. Full verification checks payload integrity, optional Ed25519 authenticity, and semantic replay of the encoded specification and submission. It does not establish that the business rules are correct, that the source data is truthful, or that a signing key belongs to a claimed identity without an independently trusted fingerprint.
