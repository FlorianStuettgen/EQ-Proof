'use strict';

const state = {
  data: null,
  catalogue: [],
  selectedCatalogueIds: null,
  customEquations: [],
  apiAvailable: false,
  exceptionFilters: { search: '', severity: 'all', domain: 'all' },
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });

function escapeHtml(value) {
  return String(value ?? '').replace(
    /[&<>"']/g,
    (character) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;',
    })[character],
  );
}

function formatMoney(value) {
  if (!Number.isFinite(Number(value))) return '—';
  const currency = state.data?.units?.currency || 'USD';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Number(value));
}

function formatResidual(value, stateValue = 'finite') {
  if (stateValue === 'non_finite') return 'non-finite';
  if (value === null || value === undefined) return '—';
  if (!Number.isFinite(Number(value))) return 'non-finite';
  const numeric = Number(value);
  return Math.abs(numeric) >= 100000
    ? formatMoney(Math.abs(numeric))
    : number.format(numeric);
}

function csvCell(value) {
  let text = String(value ?? '').replaceAll('\r', ' ').replaceAll('\n', ' ');
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, { cache: 'no-store', ...options });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    throw new Error(
      payload?.detail || `${response.status} ${response.statusText}`,
    );
  }
  return payload;
}

function setRuntimeMode() {
  const inputs = ['#p6Input', '#costInput', '#equationInput', '#compileButton'];
  inputs.forEach((selector) => {
    $(selector).disabled = !state.apiAvailable;
  });
  if (state.apiAvailable) {
    $('#apiStatus').textContent = 'Local analysis service ready. Files are processed in a request-scoped temporary directory.';
    $('#uploadButton').textContent = 'Analyze your close';
    $('#heroUploadButton').textContent = 'Use P6 + cost exports';
  } else {
    $('#apiStatus').textContent = "Public demo mode. Run `pip install -e '.[web]' && eq-controls serve` to analyze private files.";
    $('#uploadButton').textContent = 'Run locally';
    $('#heroUploadButton').textContent = 'Run locally with your files';
  }
}

async function detectApi() {
  try {
    await fetchJson('./api/health');
    state.apiAvailable = true;
  } catch {
    state.apiAvailable = false;
  }
  setRuntimeMode();
}

async function loadDemo() {
  let payload;
  try {
    payload = await fetchJson('./api/demo');
  } catch {
    payload = await fetchJson('./demo-data.json');
  }
  state.data = payload;
  state.catalogue = payload.catalogue || [];
  if (state.selectedCatalogueIds === null) {
    state.selectedCatalogueIds = new Set(
      state.catalogue.map((item) => item.id),
    );
  }
  renderAll();
  if (!state.catalogue.length) await loadCatalogue();
}

async function loadCatalogue() {
  try {
    state.catalogue = await fetchJson('./api/catalogue');
  } catch {
    state.catalogue = state.data?.catalogue || [];
  }
  if (state.selectedCatalogueIds === null) {
    state.selectedCatalogueIds = new Set(
      state.catalogue.map((item) => item.id),
    );
  }
  renderCatalogue();
}

function portfolioValue(name, fallbackName = null) {
  const portfolio = state.data?.portfolio || {};
  return portfolio[name] ?? (fallbackName ? portfolio[fallbackName] : null);
}

function renderAll() {
  const data = state.data;
  if (!data) return;
  const gate = data.gate;
  const assurance = data.assurance || {
    score: gate.confidence_score,
    label: 'legacy',
    note: 'Legacy demo payload: confidence was not a calibrated probability.',
  };
  const analysis = data.analysis;

  $('#gateLabel').textContent = gate.label;
  $('#gateHeadline').textContent = gate.headline;
  $('#assuranceValue').textContent = assurance.score ?? '—';
  $('#assuranceRing').style.setProperty(
    '--score',
    `${assurance.score ?? 0}%`,
  );
  $('#assuranceNote').textContent = assurance.note
    || 'The assurance score is a transparent severity heuristic, not a probability.';
  $('#blockerCount').textContent = gate.blockers;
  $('#failureCount').textContent = gate.failures;
  $('#recordCount').textContent = analysis.records_analyzed;
  $('#gateCard').classList.toggle('ready', gate.status === 'ready');
  $('#gateCard').classList.toggle('blocked', gate.status === 'blocked');
  $('#gateCard').classList.toggle('review', gate.status === 'review');

  $('#reportedEac').textContent = formatMoney(
    portfolioValue('reported_eac'),
  );
  $('#defensibleEac').textContent = formatMoney(
    portfolioValue('defensible_eac'),
  );
  $('#deterministicGap').textContent = formatMoney(
    portfolioValue('deterministic_forecast_gap', 'deterministic_gap'),
  );
  $('#riskAdjustedPosition').textContent = formatMoney(
    portfolioValue('reconstructed_risk_adjusted_eac', 'defensible_p80'),
  );

  const manifest = analysis.source_manifest || [];
  const sourceStrip = $('#sourceStrip');
  sourceStrip.replaceChildren(
    ...(analysis.sources || []).map((source) => {
      const chip = document.createElement('span');
      const name = source.split(/[\\/]/).pop();
      chip.textContent = name;
      const evidence = manifest.find((item) => item.name === name);
      chip.title = evidence?.sha256
        ? `${name} · sha256 ${evidence.sha256}`
        : name;
      return chip;
    }),
  );

  renderContributions();
  renderDomains();
  populateExceptionDomains();
  renderExceptions();
  renderGraph();
  renderCatalogue();
}

function renderContributions() {
  const contributions = state.data.surprise?.contributions || [];
  const maximum = Math.max(
    ...contributions.map((item) => Math.abs(
      item.exposure_above_reported_eac ?? item.hidden_exposure ?? 0,
    )),
    1,
  );
  $('#contributionCount').textContent = `${contributions.length} accounts`;
  const elements = contributions.map((item) => {
    const exposure = item.exposure_above_reported_eac
      ?? item.hidden_exposure
      ?? 0;
    const deterministic = item.deterministic_forecast_gap
      ?? item.deterministic_gap
      ?? 0;
    const risk = item.configured_risk_uplift
      ?? item.risk_exposure
      ?? 0;
    const card = document.createElement('div');
    card.className = 'contribution';
    card.dataset.recordId = item.record_id;
    const bar = document.createElement('div');
    bar.className = 'contribution-bar';
    bar.style.width = `${Math.max(
      8,
      Math.abs(exposure) / maximum * 100,
    )}%`;
    const top = document.createElement('div');
    top.className = 'contribution-top';
    const name = document.createElement('strong');
    name.textContent = item.record_id;
    const amount = document.createElement('strong');
    amount.className = 'contribution-amount';
    amount.textContent = formatMoney(exposure);
    top.append(name, amount);
    const detail = document.createElement('div');
    detail.className = 'contribution-detail';
    const pieces = [
      ['forecast gap', deterministic],
      ['pending', item.pending_change ?? 0],
      ['risk uplift', risk],
    ].map(([label, value]) => {
      const span = document.createElement('span');
      span.textContent = `${label} ${formatMoney(value)}`;
      return span;
    });
    detail.replaceChildren(...pieces);
    card.append(bar, top, detail);
    card.addEventListener('click', () => inspectContribution(item));
    return card;
  });
  $('#contributionList').replaceChildren(...elements);

  const p = state.data.portfolio;
  const bridge = [
    ['Submitted reported EAC', p.reported_eac, ''],
    [
      'Deterministic forecast contradiction',
      p.deterministic_forecast_gap ?? p.deterministic_gap,
      '+',
    ],
    [
      'Declared change + configured risk uplift',
      p.configured_change_and_risk ?? p.quantified_change_and_risk,
      '+',
    ],
    [
      'Reconstructed risk-adjusted position',
      p.reconstructed_risk_adjusted_eac ?? p.defensible_p80,
      '=',
    ],
  ].map(([label, value, symbol], index) => {
    const row = document.createElement('div');
    row.className = `bridge-row${index === 3 ? ' total' : ''}`;
    const left = document.createElement('span');
    left.textContent = `${symbol} ${label}`.trim();
    const right = document.createElement('strong');
    right.textContent = formatMoney(value);
    row.append(left, right);
    return row;
  });
  $('#reconstructionBridge').replaceChildren(...bridge);
}

function renderDomains() {
  const cards = (state.data.domain_summary || []).map((item) => {
    const card = document.createElement('div');
    card.className = 'domain-card';
    const name = document.createElement('span');
    name.textContent = item.domain.replaceAll('_', ' ');
    const count = document.createElement('strong');
    count.textContent = item.failures;
    const blocker = document.createElement('em');
    blocker.textContent = item.blockers
      ? `${item.blockers} blocker${item.blockers === 1 ? '' : 's'}`
      : 'review exception';
    card.append(name, count, blocker);
    return card;
  });
  $('#domainGrid').replaceChildren(...cards);
}

function populateExceptionDomains() {
  const select = $('#exceptionDomain');
  const current = state.exceptionFilters.domain;
  const domains = [
    ...new Set((state.data.exceptions || []).map((item) => item.domain)),
  ].sort();
  const options = [
    new Option('All', 'all'),
    ...domains.map(
      (domain) => new Option(domain.replaceAll('_', ' '), domain),
    ),
  ];
  select.replaceChildren(...options);
  select.value = domains.includes(current) ? current : 'all';
}

function renderExceptions() {
  const filters = state.exceptionFilters;
  const items = (state.data.exceptions || []).filter((item) => {
    if (
      filters.severity !== 'all'
      && item.severity !== filters.severity
    ) return false;
    if (
      filters.domain !== 'all'
      && item.domain !== filters.domain
    ) return false;
    if (!filters.search) return true;
    const haystack = [
      item.record_id,
      item.equation_id,
      item.title,
      item.remediation,
      item.expression,
    ].join(' ').toLowerCase();
    return haystack.includes(filters.search.toLowerCase());
  });
  const impactLabels = {
    deterministic_forecast_gap: 'deterministic forecast',
    risk_adjusted_reconciliation: 'risk-adjusted reconciliation',
    baseline_governance: 'baseline governance',
    earned_value_assurance: 'earned-value assurance',
    schedule_assurance: 'schedule assurance',
    close_gate: 'close gate',
  };
  const rows = items.map((item) => {
    const row = document.createElement('tr');
    const severity = document.createElement('td');
    const severityPill = document.createElement('span');
    severityPill.className = `severity ${
      ['blocker', 'major', 'minor', 'info'].includes(item.severity)
        ? item.severity
        : 'major'
    }`;
    severityPill.textContent = item.severity;
    severity.append(severityPill);
    const record = document.createElement('td');
    record.textContent = item.record_id;
    const title = document.createElement('td');
    const strong = document.createElement('strong');
    strong.textContent = item.title;
    const code = document.createElement('div');
    code.className = 'equation-meta';
    code.textContent = item.equation_id;
    title.append(strong, code);
    const residual = document.createElement('td');
    residual.textContent = formatResidual(
      item.residual,
      item.residual_state,
    );
    const impact = document.createElement('td');
    impact.textContent = impactLabels[item.impact_metric]
      || String(item.impact_metric || 'close gate').replaceAll('_', ' ');
    const action = document.createElement('td');
    action.textContent = item.remediation;
    row.append(severity, record, title, residual, impact, action);
    row.addEventListener('click', () => inspectFinding(item));
    return row;
  });
  $('#exceptionRows').replaceChildren(...rows);
  $('#exceptionFilterCount').textContent = `${items.length} of ${
    (state.data.exceptions || []).length
  }`;
}

const renderers = document.createElement('script');
renderers.src = './renderers.js';
renderers.onload = () => {
  const workflow = document.createElement('script');
  workflow.src = './workflow.js';
  document.head.append(workflow);
};
document.head.append(renderers);
