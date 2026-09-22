# EQ-Proof UI/UX audit

The hosted workbench is a functional browser application at [EQ-Proof](https://florianstuettgen.github.io/EQ-Proof/). Its initial data and three showcase cases are explicitly synthetic; visitors can also select their own files for analysis on their device.

## Experience review

The review follows a visitor from the landing page through the guided tour, example compilation, evidence inspection, file analysis, export and workspace reopening. It covers desktop, 390px mobile, 320px narrow-screen and reduced-motion behavior.

The existing dark visual system is retained. Changes address observed reachability, obstruction and semantic discrepancies:

| Finding | Correction |
| --- | --- |
| The mobile tour overlapped gate counts and inspector evidence; later steps scrolled headings behind the sticky header. | The guide sits in the document above its target, with a header offset and no automatic competing inspector. Six steps end with coverage and a brief download. |
| Keyboard activation of Next transferred focus into an automatically opened inspector. | Tour navigation keeps focus on Next; arrow keys outside the guide retain their normal behavior. |
| Landing-page exposition and a large storage toolbar delayed the active result. | A shorter introduction provides direct example and workspace entry points. Forecast explanation is expandable; secondary storage actions live under Workspace options. |
| Analyze files opened a long examples section before the actual inputs. | Your files and Examples are explicit dialog modes selected by the entry action. |
| Two mobile feature tabs were outside the visible horizontal area. | All four tabs appear in a two-column mobile layout. The evidence graph has an explicit horizontal-scroll cue and a keyboard-focusable scroll area. |
| A source-tracing promise led to inspectors without evaluated values. | Finding inspectors show equation IDs and values; account inspectors show AC and ETC when retained evidence supports them. |
| Passing and not-applicable controls could only be inspected in exported JSON. | Controls & coverage exposes results from the active analysis, separately from controls selected for the next analysis. |
| A prior search could hide every finding in the guided action step. | The guide clears unrelated filters before showing the highest-priority findings. |
| Export CSV implied that only visible filtered rows would be exported. | Export all exceptions explicitly describes the complete-register download. |
| Reopening an example replaced its identity with a generic storage-state title. | The case name and synthetic label remain visible; storage state has a separate status area. |
| A malformed workspace could partly replace the active result before reporting failure. | Imports are validated transactionally; unsuccessful imports retain the previous result. |
| A failed browser-storage write could still claim the workspace was saved. | Saving is verified and failures fall back to session-only operation with export guidance. |
| Missing AC/ETC could show a reconstructed value despite no supporting control evidence. | The UI, tour and inspectors identify unavailable reconstruction instead of presenting fallback values as proven detail. |

## Validation

Regression coverage lives in:

- `tests/ui/control-room.spec.js`: navigation, responsive tour placement, keyboard focus, tab reachability, filters, downloads and accessibility.
- `tests/ui/browser-workbench.spec.js`: file analysis, draft controls, session-only behavior, storage opt-in, failed storage and import preservation.
- `tests/ui/showcase-cases.spec.js`: all three source-backed cases, dialog modes, export/reopening, source hashes and concurrent-analysis handling.
- `tests/ui/evidence-review.spec.js`: source-value drilldown, passed and skipped controls, missing evidence and responsive accessibility.

Run `npm run test:ui` after installing the locked dependencies and Chromium. The canonical `ui-audit` workflow runs desktop, mobile and reduced-motion projects and retains failure screenshots, videos and traces. Deliberate per-project skips avoid repeating identical download and data-contract checks at every viewport.

Local Windows runs with trace/video recording have intermittently stalled while reading static HTTP response bodies. Uninstrumented local runs support visual inspection; the canonical Linux workflow remains the release gate with its configured diagnostics enabled. Test counts and deployment verification belong to the associated pull request and workflow run.

## Interpretation and storage

The gate reflects selected, applicable controls, not source completeness or management approval. A not-applicable result is not a pass. Declared change and configured risk remain separate from arithmetic forecast discrepancies; the displayed severity index is not a probability.

The hosted app is session-only by default. Remember workspace explicitly opts into browser storage; users can export JSON, reopen it, or clear saved data. The Python app processes uploads on loopback in request-scoped temporary storage. See [Runtime modes](RUNTIME_MODES.md) for the full boundary.
