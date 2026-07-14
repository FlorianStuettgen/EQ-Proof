# Threat model

EQ-Proof contains two security-relevant systems: the local project-controls Control Room and the independently versioned numerical proof engine.

## Assets

- confidentiality of uploaded P6, cost, equation-pack, change and risk exports;
- integrity of source hashes, equation manifests, findings and reconstructed states;
- availability of the local analysis process under bounded inputs;
- stable interpretation of versioned Control Room, proof and specification artifacts;
- correctness of claimed numerical repairs under the supported proof algorithm;
- confidentiality and control of private signing keys.

## Adversaries considered

1. A malicious equation author attempts to execute code or access Python objects.
2. A malformed or oversized upload attempts to exhaust memory, disk, parser, graph or browser resources.
3. An uploaded filename attempts path traversal or file collision.
4. A hostile web page attempts to address the loopback service through an untrusted host header.
5. A source record injects spreadsheet formulas into exported CSV.
6. A numeric expression produces division-by-zero, overflow, NaN or infinity.
7. A reviewer misinterprets deterministic additions as a statistical P80 or treats a triage score as a probability.
8. A graph implies financial causality that was not encoded in an equation.
9. A transport or storage actor modifies a proof after creation.
10. An actor substitutes a different public key and signature.
11. A signer knowingly signs a numerically false result.
12. Upstream data is falsified, incomplete, stale or unauthorized.

## Controls

| Threat | Control |
| --- | --- |
| Code execution through equations | Restricted AST evaluators; no `eval` or `exec` |
| Undeclared equation fields | Required-field versus expression-field validation |
| Duplicate or malformed controls | Stable-ID, schema, severity, record-type and duplicate validation |
| File abuse | 50 MiB per-file, 200 MiB aggregate and 20-file request limits |
| Adapter abuse | CSV and XER row-count limits |
| Parser abuse | Equation-count, expression-length and AST-node limits |
| Path traversal or collisions | Basename normalization plus unique temporary slot prefixes |
| Upload persistence | Request-scoped operating-system temporary directories |
| Loopback host abuse | Loopback-only CLI choices and trusted-host middleware |
| Browser injection | CSP, no external scripts, text-node rendering and escaped inspector values |
| Spreadsheet formula injection | Dangerous leading characters prefixed in CSV exports |
| Non-finite arithmetic | Explicit failure state with JSON `null`, never non-standard JSON numbers |
| Misleading risk terminology | Versioned semantic model distinguishing deterministic and risk-adjusted states |
| Invented causal impact | Domain-based declared routing; schedule findings do not acquire dollar values |
| Oversized evidence graph | Bounded account/finding nodes with explicit truncation metadata |
| Source ambiguity | SHA-256 source manifest and complete equation manifest in analysis outputs |
| Payload mutation | Canonical SHA-256 in proof artifacts |
| Key/signature substitution | Separately trusted public-key match |
| Validly signed false result | Semantic replay |
| Partial output writes | Atomic lower-engine CLI and key writes |
| Private-key exposure in repository | `.gitignore`, POSIX `0600`, explicit documentation |

## Trust boundaries

### Static demo

The hosted demo contains only synthetic generated data. It cannot analyze uploads.

### Local Control Room

The browser communicates with a loopback FastAPI service over local HTTP. Uploaded data is visible to the local host, process owner, operating system and any software already capable of reading that process or temporary directory. EQ-Proof does not claim protection from a compromised workstation.

### Source interpretation

SHA-256 demonstrates which bytes were analyzed; it does not establish that the source was truthful, approved, complete or exported from a genuine system of record.

### Equation interpretation

Passing an equation establishes consistency with that declared equation. It does not establish that the business rule was correct, sufficient or contractually authoritative.

## Explicit exclusions

EQ-Proof does not protect against:

- a compromised host or browser;
- malicious or incorrect business equations;
- falsified upstream source data;
- unauthorized but internally consistent change;
- side-channel leakage from dependencies;
- denial of service within intentionally high configured limits;
- statistical risk-model errors or unsupported percentile claims;
- identity claims without an external trust system;
- unsupported nonlinear, integer or cross-record aggregation problems;
- currency conversion or mixed-currency normalization;
- schedule-to-cost causal claims without explicit encoded relationships.

## Demonstration key

The checked-in proof-evidence public key is derived from a deterministic private seed used only inside the regeneration script. It is intentionally non-secret and must never be used for authentication, authorization or real provenance.
