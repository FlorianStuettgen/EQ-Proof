'use strict';

let tourIndex = 0;
let tourOpen = false;

function moneyFromPortfolio(name, fallback = null) {
  return formatMoney(portfolioValue(name, fallback));
}

function syncShowcaseSummary() {
  if (!state.data) return;
  const values = {
    showcaseReported: moneyFromPortfolio('reported_eac'),
    showcaseDefensible: moneyFromPortfolio('defensible_eac'),
    showcaseGap: moneyFromPortfolio('deterministic_forecast_gap', 'deterministic_gap'),
    showcaseRiskAdjusted: moneyFromPortfolio('reconstructed_risk_adjusted_eac', 'defensible_p80'),
    showcaseExposure: moneyFromPortfolio('exposure_above_reported_eac', 'hidden_exposure'),
  };
  Object.entries(values).forEach(([id, value]) => {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
  });
  const gap = $('#showcaseGap');
  if (gap) gap.parentElement.replaceChildren('Difference between supplied detail and reported forecast: ', gap, '.');
  const previewGate = $('.preview-gate');
  if (previewGate) {
    previewGate.querySelector('strong').textContent = state.data.gate.label;
    previewGate.querySelector('span').textContent = `${state.data.gate.blockers} blockers · ${state.data.gate.failures} exceptions`;
    previewGate.classList.toggle('ready', state.data.gate.status === 'ready');
    previewGate.classList.toggle('review', state.data.gate.status === 'review');
  }
  const previewValues = [
    ['.preview-metric:not(.hot) strong', values.showcaseReported],
    ['.preview-metric.hot strong', values.showcaseGap],
    ['.preview-exposure strong', values.showcaseExposure],
  ];
  previewValues.forEach(([selector, value]) => { if ($(selector)) $(selector).textContent = value; });
}

function highestExposureAccount() {
  return [...(state.data?.surprise?.contributions || [])].sort(
    (left, right) => Math.abs(right.exposure_above_reported_eac ?? right.hidden_exposure ?? 0)
      - Math.abs(left.exposure_above_reported_eac ?? left.hidden_exposure ?? 0),
  )[0] || null;
}

function forecastDetailAvailable(recordId = null) {
  if (!Array.isArray(state.data.analysis?.findings)) return null;
  const checks = (state.data.analysis?.findings || []).filter((finding) => finding.equation_id === 'cost.eac_identity'
    && (!recordId || finding.record_id === recordId));
  const expected = recordId ? 1 : state.data.portfolio?.accounts_reconstructed;
  return expected > 0 && checks.length === expected && checks.every((finding) => ['pass', 'fail'].includes(finding.status)
    && Number.isFinite(finding.values?.AC) && Number.isFinite(finding.values?.ETC));
}

const tourSteps = [
  {
    eyebrow: 'Step 1 · decision', title: 'Start at the gate', target: '[data-tour-target="gate"]', tab: 'overview',
    body: () => `${state.data.gate.label} follows ${state.data.gate.failures} failed controls, including ${state.data.gate.blockers} blockers, across ${state.data.analysis.records_analyzed} source records. Only selected, applicable controls contribute to the gate.`,
    action: () => closeInspector(),
  },
  {
    eyebrow: 'Step 2 · reconstruction', title: 'Check the forecast arithmetic', target: '[data-tour-target="gap"]', tab: 'overview',
    body: () => {
      const gap = portfolioValue('deterministic_forecast_gap', 'deterministic_gap');
      const coverage = forecastDetailAvailable();
      if (gap === null || gap === undefined || coverage === false) return 'The executed controls do not establish complete AC + ETC coverage. Missing evidence does not establish that the forecast reconciles; inspect applicability and supplied fields.';
      if (coverage === null) return `The displayed reported EAC is ${moneyFromPortfolio('reported_eac')} and detail reconstruction is ${moneyFromPortfolio('defensible_eac')}, a ${formatMoney(gap)} arithmetic difference. This compact artifact omits per-check coverage; inspect its source evidence.`;
      const result = gap === 0
        ? 'The forecast reconciles to its supplied detail. This does not establish commercial or contractual correctness.'
        : `The ${formatMoney(gap)} difference is a direct deterministic contradiction, separate from declared change and risk.`;
      return `Reported EAC is ${moneyFromPortfolio('reported_eac')}, while AC + ETC reconstructs to ${moneyFromPortfolio('defensible_eac')}. ${result}`;
    },
    action: () => inspectMetric('deterministic_forecast_gap'),
  },
  {
    eyebrow: 'Step 3 · material account', title: 'Inspect the largest account', target: '[data-tour-target="account"]', tab: 'overview',
    body: () => {
      const account = highestExposureAccount();
      if (!account) return 'Account-level reconstruction is unavailable for this data set.';
      const exposure = account.exposure_above_reported_eac ?? account.hidden_exposure ?? 0;
      const deterministic = account.deterministic_forecast_gap ?? account.deterministic_gap ?? 0;
      if (forecastDetailAvailable(account.record_id) !== true) return `${account.record_id} has a displayed position ${formatMoney(exposure)} above reported EAC, with a ${formatMoney(deterministic)} forecast difference. Complete AC + ETC coverage has not been established; inspect its supplied fields and applicable checks.`;
      return `${account.record_id} contributes ${formatMoney(exposure)} above reported EAC. ${deterministic === 0 ? 'Its supplied forecast detail reconciles; the remaining amount is declared change and risk.' : `${formatMoney(deterministic)} is a deterministic forecast contradiction.`}`;
    },
    action: () => {
      closeInspector();
      const account = highestExposureAccount();
      if (account) inspectContribution(account);
    },
  },
  {
    eyebrow: 'Step 4 · lineage', title: 'Trace source to decision', target: '[data-tour-target="graph"]', tab: 'graph',
    body: () => 'The graph preserves declared lineage: source record → failed equation → affected metric or assurance domain → close gate.',
    action: () => closeInspector(),
  },
  {
    eyebrow: 'Step 5 · action', title: 'Review the required actions', target: '[data-tour-target="exceptions"]', tab: 'exceptions',
    body: () => state.data.gate.failures
      ? 'The exception register ranks failures, retains the exact equation and residual, and provides the required action.'
      : 'No selected, applicable controls failed. Review missing or not-applicable checks and the governance boundary before relying on this result.',
    action: () => {
      closeInspector();
      state.exceptionFilters.severity = state.data.gate.blockers ? 'blocker' : 'all';
      $('#exceptionSeverity').value = state.exceptionFilters.severity;
      renderExceptions();
    },
  },
];

function clearTourFocus() {
  $$('.tour-focus').forEach((element) => element.classList.remove('tour-focus'));
}

function showTourStep(index) {
  if (!state.data || typeof activateTab !== 'function') return;
  tourIndex = Math.max(0, Math.min(index, tourSteps.length - 1));
  const step = tourSteps[tourIndex];
  if (step.tab) activateTab(step.tab);
  step.action?.();
  clearTourFocus();
  const target = $(step.target);
  if (target) {
    target.classList.add('tour-focus');
    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  $('#tourProgress').textContent = `${tourIndex + 1} / ${tourSteps.length}`;
  $('#tourEyebrow').textContent = step.eyebrow;
  $('#tourTitle').textContent = step.title;
  $('#tourBody').textContent = step.body();
  $('#tourBack').disabled = tourIndex === 0;
  $('#tourNext').textContent = tourIndex === tourSteps.length - 1 ? 'Finish' : 'Next';
}

function startTour() {
  if (!state.data || typeof activateTab !== 'function') return;
  tourOpen = true;
  $('#tourCard').hidden = false;
  showTourStep(0);
}

function closeTour() {
  tourOpen = false;
  $('#tourCard').hidden = true;
  clearTourFocus();
  closeInspector?.();
}

function nextTourStep() {
  if (tourIndex >= tourSteps.length - 1) closeTour();
  else showTourStep(tourIndex + 1);
}

function previousTourStep() {
  if (tourIndex > 0) showTourStep(tourIndex - 1);
}

function markdownCell(value) {
  return String(value ?? '').replaceAll('|', '\\|').replaceAll('`', '\\`').replaceAll('\n', ' ');
}

function buildExecutiveBrief() {
  const data = state.data;
  const portfolio = data.portfolio || {};
  const sources = data.analysis?.source_manifest || [];
  const exceptions = data.exceptions || [];
  const blockers = exceptions.filter((item) => item.severity === 'blocker');
  const caseNote = data.demo?.synthetic
    ? `Synthetic showcase example: **${markdownCell(data.demo.name)}**. These constructed inputs are not a real project approval.\n\n`
    : '';
  const coverage = forecastDetailAvailable();
  const reconstructionNote = coverage === false
    ? 'Forecast reconciliation is unavailable: executed controls do not evidence complete AC + ETC coverage.\n\n'
    : coverage === null ? 'This compact artifact omits per-check coverage; inspect the original source evidence before relying on reconciliation.\n\n' : '';
  const detailValue = coverage === false ? 'Unavailable — AC and ETC not evidenced' : formatMoney(portfolio.defensible_eac);
  const gapValue = coverage === false ? 'Unavailable — AC and ETC not evidenced' : formatMoney(portfolio.deterministic_forecast_gap ?? portfolio.deterministic_gap);
  const sourceLines = sources.length
    ? sources.map((item) => `- \`${markdownCell(item.name)}\` — SHA-256 \`${markdownCell(item.sha256)}\``).join('\n')
    : '- No source manifest supplied.';
  const exceptionRows = exceptions.slice(0, 8).length
    ? exceptions.slice(0, 8).map((item) => `| ${markdownCell(item.severity)} | ${markdownCell(item.record_id)} | ${markdownCell(item.title)} | ${markdownCell(item.remediation)} |`).join('\n')
    : '| — | — | No exceptions | Review applicability, source completeness and approval boundary |';
  return `# EQ-Proof Executive Close Brief\n\n${caseNote}${reconstructionNote}## Decision\n\n**${data.gate.label}** — ${data.gate.headline}\n\n| Decision state | Value |\n| --- | ---: |\n| Reported EAC | ${formatMoney(portfolio.reported_eac)} |\n| Detail-reconstructed EAC (AC + ETC) | ${detailValue} |\n| Deterministic forecast gap | ${gapValue} |\n| Declared change and configured risk | ${formatMoney(portfolio.configured_change_and_risk ?? portfolio.quantified_change_and_risk)} |\n| Reconstructed risk-adjusted position | ${formatMoney(portfolio.reconstructed_risk_adjusted_eac ?? portfolio.defensible_p80)} |\n| Exposure above reported EAC | ${formatMoney(portfolio.exposure_above_reported_eac ?? portfolio.hidden_exposure)} |\n\n## Control summary\n\n- Records analyzed: **${data.analysis.records_analyzed}**\n- Equations executed: **${data.analysis.equations_executed}**\n- Not-applicable checks: **${data.analysis.summary?.not_applicable ?? '—'}**\n- Blockers: **${blockers.length}**\n- Total exceptions: **${exceptions.length}**\n- Control severity index: **${data.assurance?.score ?? '—'} / 100** — severity heuristic, not a probability\n\n## Ranked actions\n\n| Severity | Source record | Control | Required action |\n| --- | --- | --- | --- |\n${exceptionRows}\n\n## Source evidence\n\n${sourceLines}\n\n## Interpretation boundary\n\nThis brief reports internal consistency under the selected and applicable equations. It does not certify contractual truth, approve change, replace Primavera P6 calculations, perform currency conversion, or calculate probabilistic risk.\n`;
}

function exportExecutiveBrief() {
  if (!state.data || typeof downloadBlob !== 'function') return;
  const name = state.data.demo?.name || 'monthly-close';
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'monthly-close';
  downloadBlob(buildExecutiveBrief(), 'text/markdown', `eq-proof-${slug}-executive-brief.md`);
}

function initShowcase() {
  ['#guidedDemoButton', '#workspaceTourButton'].forEach((selector) => $(selector)?.addEventListener('click', startTour));
  $('#tourClose')?.addEventListener('click', closeTour);
  $('#tourNext')?.addEventListener('click', nextTourStep);
  $('#tourBack')?.addEventListener('click', previousTourStep);
  $('#downloadBriefButton')?.addEventListener('click', exportExecutiveBrief);
  document.addEventListener('keydown', (event) => {
    const formControl = event.target?.matches?.('input, textarea, select, [contenteditable="true"]');
    if (formControl && ['ArrowRight', 'ArrowLeft'].includes(event.key)) return;
    if (event.key === 'Escape' && tourOpen) closeTour();
    if (event.key === 'ArrowRight' && tourOpen) nextTourStep();
    if (event.key === 'ArrowLeft' && tourOpen) previousTourStep();
  });
  const metricGrid = document.querySelector('.metric-grid');
  if (metricGrid) new MutationObserver(syncShowcaseSummary).observe(metricGrid, { childList: true, subtree: true, characterData: true });
  syncShowcaseSummary();
}

initShowcase();

const audit = document.createElement('script');
audit.src = './audit.js';
audit.onerror = () => console.error('EQ-Proof interaction hardening failed to load.');
document.head.append(audit);

const browserBridge = document.createElement('script');
browserBridge.src = './browser-bridge.js';
browserBridge.onerror = () => console.error('EQ-Proof browser workbench failed to load.');
document.head.append(browserBridge);
