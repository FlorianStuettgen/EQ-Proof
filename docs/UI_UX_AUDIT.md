# EQ-Proof UI/UX Audit

This audit covers the hosted synthetic Control Room at:

`https://florianstuettgen.github.io/EQ-Proof/`

## Scope

The automated browser matrix exercises:

- desktop Chromium;
- a 390 × 844 mobile viewport with touch input;
- reduced-motion preferences;
- initial demo loading and deterministic values;
- public-versus-local runtime messaging;
- local-analysis dialog opening and closing;
- tab semantics and keyboard navigation;
- inspector focus management;
- guided-tour completion and focus restoration;
- keyboard activation of account contributions and exception rows;
- exception filtering and empty states;
- browser-side structural validation for draft equations;
- executive-brief and CSV downloads;
- page-level horizontal overflow; and
- automated WCAG A/AA and best-practice checks for serious or critical findings.

## Defects corrected

1. **The dialog close control submitted the analysis form.**
   The close button had the default submit type inside a form whose submit handler prevents native dialog closure. It is now an explicit button with a dedicated close action.

2. **The closed inspector remained keyboard-focusable.**
   The off-canvas inspector used `aria-hidden` without removing its controls from the tab sequence. Closed state now uses `inert`, and open/close transitions manage focus.

3. **Tabs were incomplete for keyboard and assistive technology users.**
   Tabs now expose `aria-controls`, `aria-selected`, roving `tabindex`, labelled panels, hidden inactive panels, and Left/Right/Home/End keyboard navigation.

4. **Account cards and exception rows were mouse-only.**
   Interactive generated records now receive keyboard focus, accessible labels, and Enter/Space activation.

5. **Interactive SVG nodes lacked dependable accessible names.**
   Evidence nodes now expose labels derived from their node type, record, and equation metadata, and Space no longer scrolls the page while activating a node.

6. **Public equation authoring overstated validation.**
   Public mode now says `Add to draft pack`, distinguishes structural checks from authoritative engine validation, rejects multiple comparisons, invalid identifiers, statement separators, and oversized expressions, and deduplicates required fields.

7. **Empty result states rendered as blank panels.**
   Control-account, domain, and exception areas now explain when no records or filtered results are available.

8. **Generated downloads used a fragile object-URL lifecycle.**
   Download anchors are attached before activation and object URLs are revoked after the browser has had time to begin the download. CSV output also includes a UTF-8 BOM for spreadsheet compatibility.

9. **Reduced-motion settings did not cover JavaScript scrolling.**
   Smooth `scrollIntoView` calls are normalized to immediate movement for users who request reduced motion.

10. **The deployment pipeline did not prove these interaction assets existed.**
    Pages validation and repository JavaScript checks now require the audit CSS and JavaScript, while a dedicated Playwright workflow preserves browser-level regression coverage.

## Evidence

The audit is implemented in:

- `tests/ui/control-room.spec.js`;
- `playwright.config.js`; and
- `.github/workflows/ui-audit.yml`.

Failure artifacts retain the Playwright HTML report, screenshots, videos, and traces for fourteen days.
