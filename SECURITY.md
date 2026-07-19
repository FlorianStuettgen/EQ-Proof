# Security policy

## Reporting

Please report suspected vulnerabilities privately through GitHub's security advisory interface. Do not open a public issue containing exploit details, private project data, private keys or sensitive proof artifacts.

A useful report identifies the affected version or commit, runtime mode, smallest synthetic reproduction, observed result, expected result and whether the issue crosses a documented data-handling or trust boundary.

## Supported versions

| Version | Supported |
| --- | --- |
| 1.5.x | Yes |
| 1.4.x | Security fixes only |
| 1.3.x and earlier | No |

The lower proof and specification artifact contracts are versioned independently inside their payloads. Package support does not silently change the interpretation of an older artifact contract.

## Product security boundaries

EQ-Proof has distinct hosted-browser, loopback-local and CLI runtime modes. [Runtime Modes and Data Handling](docs/RUNTIME_MODES.md) is the canonical movement and persistence contract.

### Hosted browser workbench

The GitHub Pages application can process user-selected generic CSV, Primavera P6 XER and JSON equation-pack files entirely in the browser. It has no EQ-Proof upload endpoint and loads no external scripts, fonts, models, analytics or telemetry. Project files are not sent to an EQ-Proof server, third-party API or model endpoint.

The browser workbench is session-only by default. The complete schema-versioned Control Room JSON is written to browser local storage only when the user explicitly enables **Remember workspace on this browser**. Disabling persistence or selecting **Clear saved workspace** removes that stored workspace while leaving the current page available for the session.

A saved Control Room workspace may include normalized source records, source names and hashes, equation definitions, findings and reconstructed values. Browser-local processing does not protect those values from a compromised device, malicious extension, shared browser profile, local administrator or other software with access to site storage.

### Local Control Room

`eq-controls serve` binds only to a loopback host selected from `127.0.0.1`, `localhost` or `::1`. Trusted-host middleware rejects other host headers.

Local controls include:

- restrictive Content Security Policy and browser hardening headers;
- 50 MiB per-file, 200 MiB per-request and 20-file limits;
- equation-count, expression-size, AST-node and adapter-row limits;
- request-scoped operating-system temporary directories;
- unique temporary filenames and basename normalization;
- no upload persistence or telemetry;
- server-side validation of browser-authored equations;
- spreadsheet-formula neutralization in CSV exports; and
- JSON-safe representation of non-finite arithmetic failures.

The application uses local HTTP between the browser and the loopback FastAPI process. It does not require outbound network access for analysis. Files explicitly downloaded or written by the user remain subject to the surrounding filesystem and retention controls.

### CLI and proof modes

The project-controls and numerical-proof CLIs read and write only the paths supplied by the user. EQ-Proof does not provide centralized retention, remote deletion, enterprise identity, data-loss prevention, HSM or KMS capabilities.

## Equation safety

Project-controls equations use a restricted parser and evaluator. They permit finite numeric constants, declared fields, arithmetic, one comparison and an allow-listed function set. They reject imports, attributes, assignment, executable statements, unsupported operators, undeclared expression fields, duplicate IDs, oversized expressions, oversized syntax trees and oversized equation packs.

The lower linear-repair specification language uses its own allow-listed compiler. Neither engine evaluates supplied equations as Python or JavaScript source.

## Proof security properties

Full proof verification checks three distinct properties:

1. canonical payload integrity through SHA-256;
2. optional Ed25519 signature validity and trusted-key matching; and
3. semantic replay of the encoded specification, submission, result, movement, objective and diagnostics.

A signature alone is not treated as proof of numerical correctness. A source hash does not establish source-system authenticity, contractual truth, authorization or completeness before ingestion.

## Key handling

- Keep private keys outside the repository and normal output directories.
- Restrict filesystem access; generated private keys use mode `0600` on POSIX systems.
- Distribute trusted public keys or fingerprints through an independent channel.
- Rotate keys according to the surrounding organization's policy.
- Never use the deterministic demonstration key for real authentication, authorization or provenance.

EQ-Proof is not a key-management service and does not provide HSM, KMS, certificate, revocation or organizational identity infrastructure.

See [Threat Model](docs/THREAT_MODEL.md) for assets, adversaries, controls and exclusions.
