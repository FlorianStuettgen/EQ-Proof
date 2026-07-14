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
}

function highestExposureAccount() {
  return [...(state.data?.surprise?.contributions || [])].sort(
    (left, right) => Math.abs(
      right.exposure_above_reported_eac ?? right.hidden_exposure ?? 0,
    ) - Math.abs(
      left.exposure_above_reported_eac ?? left.hidden_exposure ?? 0,
    ),
  )[0] || null;
}

const tourSteps = [
  {
    eyebrow: 'Step 1 · decision',
    title: 'Start at the gate',
    target: '[data-tour-target="gate"]',
    tab: 'overview',
    body: () => `${state.data.gate.label} is not a decorative status. It is derived from ${state.data.gate.blockers} blocker-level equation failures across ${state.data.analysis.records_analyzed} source records.`,
    action: () => closeInspector(),
  },
  {
    eyebrow: 'Step 2 · contradiction',
    title: 'Separate the arithmetic error',
    target: '[data-tour-target="gap"]',
    tab: 'overview',
    body: () => `Reported EAC is ${moneyFromPortfolio('reported_eac')}, while governed AC + ETC reconstructs to ${moneyFromPortfolio('defensible_eac')}. The ${moneyFromPortfolio('deterministic_forecast_gap', 'deterministic_gap')} difference is a direct internal contradiction—not a risk opinion.`,
    action: () => inspectMetric('deterministic_forecast_gap'),
  },
  {
    eyebrow: 'Step 3 · material account',
    title: 'Find where the surprise comes from',
    target: '[data-tour-target="account"]',
    tab: 'overview',
    body: () => {
      const account = highestExposureAccount();
      if (!account) return 'Account-level reconstruction is unavailable for this data set.';
      const exposure = account.exposure_above_reported_eac ?? account.hidden_exposure ?? 0;
      const deterministic = account.deterministic_forecast_gap ?? account.deterministic_gap ?? 0;
      return `${account.record_id} contributes ${formatMoney(exposure)} above reported EAC, including ${formatMoney(deterministic)} of deterministic forecast contradiction. Click the account after the tour to inspect every component.`;
    },
    action: () => {
      closeInspector();
      const account = highestExposureAccount();
      if (account) inspectContribution(account);
    },
  },
  {
    eyebrow: 'Step 4 · lineage',
    title: 'Trace source to decision',
    target: '[data-tour-target="graph"]',
    tab: 'graph',
    body: () => 'The graph preserves declared lineage: source record → failed equation → affected metric or assurance domain → close gate. Schedule findings stay in schedule assurance unless an explicit equation provides a monetary relationship.',
    action: () => closeInspector(),
  },
  {
    eyebrow: 'Step 5 · action',
    title: 'Turn the finding into work',
    target: '[data-tour-target="exceptions"]',
    tab: 'exceptions',
    body: () => 'The exception register ranks failures by severity and materiality, retains the exact equation and residual, and provides the required action. Export it to CSV or download the executive brief for the close-review package.',
    action: () => {
      closeInspector();
      state.exceptionFilters.severity = 'blocker';
      $('#exceptionSeverity').value = 'blocker';
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
  if (step.action) step.action();
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
  if (typeof closeInspector === 'function') closeInspector();
}

function nextTourStep() {
  if (tourIndex >= tourSteps.length - 1) {
    closeTour();
    return;
  }
  showTourStep(tourIndex + 1);
}

function previousTourStep() {
  if (tourIndex > 0) showTourStep(tourIndex - 1);
}

function markdownCell(value) {
  return String(value ?? '').replaceAll('|', '\\|').replaceAll('\n', ' ');
}

function buildExecutiveBrief() {
  const data = state.data;
  const portfolio = data.portfolio || {};
  const sources = data.analysis?.source_manifest || [];
  const exceptions = data.exceptions || [];
  const blockers = exceptions.filter((item) => item.severity === 'blocker');
  const topExceptions = exceptions.slice(0, 8);
  const sourceLines = sources.length
    ? sources.map((item) => `- \`${markdownCell(item.name)}\` — SHA-256 \`${markdownCell(item.sha256)}\``).join('\n')
    : (data.analysis?.sources || []).map((item) => `- \`${markdownCell(item)}\``).join('\n') || '- No source manifest supplied.';
  const exceptionRows = topExceptions.length
    ? topExceptions.map((item) => `| ${markdownCell(item.severity)} | ${markdownCell(item.record_id)} | ${markdownCell(item.title)} | ${markdownCell(item.remediation)} |`).join('\n')
    : '| — | — | No exceptions | No action required |';

  return `# EQ-Proof Executive Close Brief\n\n## Decision\n\n**${data.gate.label}** — ${data.gate.headline}\n\n| Decision state | Value |\n| --- | ---: |\n| Reported EAC | ${formatMoney(portfolio.reported_eac)} |\n| Defensible EAC (AC + ETC) | ${formatMoney(portfolio.defensible_eac)} |\n| Deterministic forecast gap | ${formatMoney(portfolio.deterministic_forecast_gap ?? portfolio.deterministic_gap)} |\n| Declared change and configured risk | ${formatMoney(portfolio.configured_change_and_risk ?? portfolio.quantified_change_and_risk)} |\n| Reconstructed risk-adjusted position | ${formatMoney(portfolio.reconstructed_risk_adjusted_eac ?? portfolio.defensible_p80)} |\n| Exposure above reported EAC | ${formatMoney(portfolio.exposure_above_reported_eac ?? portfolio.hidden_exposure)} |\n\n## Control summary\n\n- Records analyzed: **${data.analysis.records_analyzed}**\n- Equations executed: **${data.analysis.equations_executed}**\n- Blockers: **${blockers.length}**\n- Total exceptions: **${exceptions.length}**\n- Assurance score: **${data.assurance?.score ?? '—'} / 100** — severity heuristic, not a probability\n\n## Ranked actions\n\n| Severity | Source record | Control | Required action |\n| --- | --- | --- | --- |\n${exceptionRows}\n\n## Source evidence\n\n${sourceLines}\n\n## Interpretation boundary\n\nThis brief reports internal consistency under the selected and applicable equations. It does not certify contractual truth, approve change, replace Primavera P6 calculations, perform currency conversion, or calculate probabilistic risk.\n`;
}

function exportExecutiveBrief() {
  if (!state.data || typeof downloadBlob !== 'function') return;
  const name = state.data.demo?.name || 'monthly-close';
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'monthly-close';
  downloadBlob(buildExecutiveBrief(), 'text/markdown', `eq-proof-${slug}-executive-brief.md`);
}

function initShowcase() {
  ['#guidedDemoButton', '#workspaceTourButton'].forEach((selector) => {
    $(selector)?.addEventListener('click', startTour);
  });
  $('#tourClose')?.addEventListener('click', closeTour);
  $('#tourNext')?.addEventListener('click', nextTourStep);
  $('#tourBack')?.addEventListener('click', previousTourStep);
  $('#downloadBriefButton')?.addEventListener('click', exportExecutiveBrief);
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && tourOpen) closeTour();
    if (event.key === 'ArrowRight' && tourOpen) nextTourStep();
    if (event.key === 'ArrowLeft' && tourOpen) previousTourStep();
  });
  const metricGrid = document.querySelector('.metric-grid');
  if (metricGrid) {
    new MutationObserver(syncShowcaseSummary).observe(metricGrid, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }
  syncShowcaseSummary();
}

initShowcase();
