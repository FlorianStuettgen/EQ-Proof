# Security policy

## Reporting

Please report suspected vulnerabilities privately through GitHub's security advisory interface. Do not open a public issue containing exploit details, private project data, private keys, or sensitive proof artifacts.

## Supported versions

| Version | Supported |
| --- | --- |
| 1.4.x | Yes |
| 1.3.x | Security fixes only |
| 1.2.x and earlier | No |

The lower proof and specification artifact contracts are versioned independently inside their payloads.

## Product security boundaries

EQ-Proof has two distinct runtime modes.

### Static public demo

The GitHub Pages application is synthetic-data-only. It has no upload or analysis endpoint and loads no external scripts, fonts, models, analytics, or telemetry.

### Local Control Room

`eq-controls serve` binds only to a loopback host selected from `127.0.0.1`, `localhost`, or `::1`. Trusted-host middleware rejects other host headers.

Local controls include:

- restrictive Content Security Policy and browser hardening headers;
- 50 MiB per-file, 200 MiB per-request and 20-file limits;
- equation-count, expression-size, AST-node and adapter-row limits;
- request-scoped operating-system temporary directories;
- unique temporary filenames and basename normalization;
- no upload persistence or telemetry;
- server-side validation of browser-authored equations;
- spreadsheet-formula neutralization in CSV exports;
- JSON-safe representation of non-finite arithmetic failures.

The application uses local HTTP between the browser and the loopback FastAPI process. It does not require outbound network access for analysis.

## Equation safety

Project-controls equations use a restricted AST evaluator. It permits finite numeric constants, declared fields, arithmetic, one comparison, and an allow-listed function set. It rejects imports, attributes, assignment, executable statements, unsupported operators, undeclared expression fields, duplicate IDs, oversized expressions, oversized syntax trees, and oversized equation packs.

The lower linear-repair specification language uses its own allow-listed compiler. Neither engine evaluates supplied equations as Python source.

## Proof security properties

Full proof verification checks three distinct properties:

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

See [Threat model](docs/THREAT_MODEL.md) for assets, adversaries, controls, and exclusions.
