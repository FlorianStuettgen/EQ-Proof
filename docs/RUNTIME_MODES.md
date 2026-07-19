# Runtime modes and data handling

This document is the canonical boundary for where EQ-Proof executes, how project files move, and what can remain after a session. The README, product architecture and security policy must not describe a runtime mode differently from this contract.

## Mode summary

| Mode | Intended use | Where analysis runs | File movement | Persistence |
| --- | --- | --- | --- | --- |
| Hosted browser workbench | Evaluation, portable local analysis and synthetic demonstrations | JavaScript engine in the visitor's browser | User-selected CSV, P6 XER and equation files are read by the browser and are not uploaded to EQ-Proof | Session-only by default; complete Control Room JSON is stored in browser local storage only after explicit opt-in |
| Local Control Room | Local analysis through the Python implementation and browser interface | Python/FastAPI on a loopback address | The browser sends selected files only to the loopback process on the same device | Uploads use a request-scoped operating-system temporary directory and are deleted after the response; exported files persist only where the user saves them |
| CLI | Automated close gates and batch workflows | Python process on the local or controlled execution host | Files are read from paths supplied to the command | Outputs persist only in the explicitly selected output directory |
| Numerical proof CLI | Deterministic numerical repair, signing and semantic replay | Python process on the local or controlled execution host | Specifications, submissions, proofs and keys are local files | Proofs and reports persist where explicitly written; private-key custody remains outside EQ-Proof |

## Hosted browser workbench

The GitHub Pages application is a functional local browser workbench, not a server-side upload application. It can parse generic project-controls CSV exports, Primavera P6 XER `TASK` records and JSON equation packs. It can also execute browser-authored equations through the restricted browser parser.

Selected files are exposed to the page by the browser and processed in browser memory. EQ-Proof does not provide an upload endpoint for the hosted application, and the application does not send project files to an EQ-Proof server, analytics service, model endpoint or third-party API.

### Storage policy

The hosted workbench is **session-only by default**:

- completed analysis remains available while the page is open;
- exports occur only when the user selects a download action;
- the complete Control Room workspace is not retained in browser local storage by default; and
- closing or reloading the page returns to the deterministic demonstration unless persistence was enabled.

The **Remember workspace on this browser** control is an explicit opt-in. When enabled, EQ-Proof stores the complete schema-versioned Control Room JSON in browser local storage so it can be restored later. That artifact may include normalized source records, source names, source hashes, equation definitions, findings and reconstructed values. It remains until the user clears it, resets the workspace or browser/site storage is removed.

The workbench exposes a **Clear saved workspace** action. Disabling persistence removes the saved workspace while leaving the active page available as a session-only workspace.

Local processing does not protect data from a compromised device, malicious browser extension, shared browser profile, local administrator or other software with access to browser storage. Use the hosted workbench only on an appropriate device and browser profile.

## Local Control Room

`eq-controls serve` binds to an allow-listed loopback host. The browser sends selected files to the local FastAPI process over local HTTP. The server writes uploads to uniquely named files in a request-scoped operating-system temporary directory, executes the Python adapters and control engine, returns the result, and removes the temporary directory when the request completes.

The local application applies trusted-host checks, request and row limits, restrictive browser headers, safe equation evaluation, filename normalization, output escaping and spreadsheet-formula neutralization. It does not require outbound network access for analysis.

The temporary-file lifecycle does not govern files explicitly downloaded or written by the user. Those files remain subject to the user's filesystem, retention and access-control practices.

## CLI modes

The project-controls CLI reads the paths named in the command and writes analysis artifacts to the selected output directory. The lower numerical proof CLI similarly reads specifications and submissions and writes proofs or reports to explicit paths.

EQ-Proof does not provide enterprise secret storage, centralized retention, remote deletion, data-loss prevention, key management or organizational identity controls. Those controls belong to the surrounding environment.

## Shared boundaries

Across all modes:

- EQ-Proof evaluates declared data and equations; it does not establish that source records were truthful, authorized or complete before ingestion.
- Source hashes provide integrity and replay evidence, not source-system authenticity or contractual truth.
- `CLOSE READY` means no selected, applicable control failed. It is not contractual certification or management approval.
- The reconstructed `AC + ETC` state is an arithmetic reconciliation, not an independent commercial forecast.
- Deterministic addition of supplied change and risk values is not a statistical P80 calculation.

## Change-control rule

Any change to hosted file handling, browser persistence, loopback upload handling, CLI persistence, telemetry, external dependencies or outbound network behavior must update this document and add or revise an automated contract test in the same pull request.
