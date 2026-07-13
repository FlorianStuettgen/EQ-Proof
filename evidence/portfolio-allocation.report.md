# EQ-Proof Repair Report

## Decision record

| Field | Value |
| --- | --- |
| Specification | `portfolio-allocation` |
| Status | `repaired` |
| Euclidean movement | `0.0707106781187` |
| Maximum violation before | `0.1` |
| Maximum violation after | `0` |
| Algorithm | `Dykstra Euclidean projection` |
| Iterations | `2` |
| Attestation | `Ed25519` |
| Signer fingerprint | `cb6991cf3bd81a482995b73f34d11d0a60546917d790a38d82c32461ea6c2292` |

## Values

| Variable | Submitted | Repaired | Delta |
| --- | ---: | ---: | ---: |
| `forecast_a` | 0.55 | 0.5 | -0.05 |
| `forecast_b` | 0.35 | 0.3 | -0.05 |
| `forecast_c` | 0.2 | 0.2 | 0 |

## Violations detected before repair

- `allocation-total`: violation `0.1` — `forecast_a + forecast_b + forecast_c == 1`

## Verification boundary

This report is a convenience view. The JSON proof is authoritative. Verification establishes artifact integrity and, for Ed25519 mode, possession of the corresponding private key. It does not establish that the business rules are correct or that the key belongs to a particular organization unless the fingerprint is trusted independently.
