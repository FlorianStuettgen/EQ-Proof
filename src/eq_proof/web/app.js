'use strict';

const state = {
  data: null,
  catalogue: [],
  customEquations: [],
  apiAvailable: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', notation: 'compact', maximumFractionDigits: 1 });
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}

function formatMoney(value) {
  return Number.isFinite(Number(value)) ? money.format(Number(value)) : '—';
}

function formatResidual(value) {
  if (value === null || value === undefined) return '—';
  if (!Number.isFinite(Number(value))) return '∞';
  const numeric = Number(value);
  return Math.abs(numeric) >= 100000 ? money.format(Math.abs(numeric)) : number.format(numeric);
}

function escapeCsv(value) {
  const text = String(value ?? '');
  return `"${text.replaceAll('"', '""')}"`;
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function detectApi() {
  try {
    await fetchJson('./api/health');
    state.apiAvailable = true;
    $('#apiStatus').textContent = 'Local analysis service ready. Files are processed on this machine.';
  } catch {
    state.apiAvailable = false;
    $('#apiStatus').textContent = 'Public demo mode. Run `eq-controls serve` locally to analyze private files.';
  }
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
  renderAll();
  if (!state.catalogue.length) await loadCatalogue();
}

async function loadCatalogue() {
  try {
    state.catalogue = await fetchJson('./api/catalogue');
  } catch {
    state.catalogue = state.data?.catalogue || [];
  }
  renderCatalogue();
}

function renderAll() {
  const data = state.data;
  if (!data) return;
  const gate = data.gate;
  const portfolio = data.portfolio;
  const analysis = data.analysis;

  $('#gateLabel').textContent = gate.label;
  $('#gateHeadline').textContent = gate.headline;
  $('#confidenceValue').textContent = gate.confidence_score;
  $('#confidenceRing').style.setProperty('--score', `${gate.confidence_score}%`);
  $('#blockerCount').textContent = gate.blockers;
  $('#failureCount').textContent = gate.failures;
  $('#recordCount').textContent = analysis.records_analyzed;
  $('#gateCard').classList.toggle('ready', gate.status === 'ready');
  $('#gateCard').classList.toggle('blocked', gate.status !== 'ready');

  $('#reportedEac').textContent = formatMoney(portfolio.reported_eac);
  $('#defensibleEac').textContent = formatMoney(portfolio.defensible_eac);
  $('#defensibleP80').textContent = formatMoney(portfolio.defensible_p80);
  $('#hiddenExposure').textContent = formatMoney(portfolio.hidden_exposure);

  const sourceStrip = $('#sourceStrip');
  sourceStrip.replaceChildren(...(analysis.sources || []).map((source) => {
    const chip = document.createElement('span');
    chip.textContent = source.split(/[\\/]/).pop();
    chip.title = source;
    return chip;
  }));

  renderContributions();
  renderDomains();
  renderExceptions();
  renderGraph();
  renderCatalogue();
}

function renderContributions() {
  const contributions = state.data.surprise.contributions || [];
  const maximum = Math.max(...contributions.map((item) => Math.abs(item.hidden_exposure)), 1);
  $('#contributionCount').textContent = `${contributions.length} accounts`;
  const elements = contributions.map((item) => {
    const card = document.createElement('div');
    card.className = 'contribution';
    card.dataset.recordId = item.record_id;
    const bar = document.createElement('div');
    bar.className = 'contribution-bar';
    bar.style.width = `${Math.max(8, Math.abs(item.hidden_exposure) / maximum * 100)}%`;
    const top = document.createElement('div');
    top.className = 'contribution-top';
    const name = document.createElement('strong');
    name.textContent = item.record_id;
    const amount = document.createElement('strong');
    amount.className = 'contribution-amount';
    amount.textContent = formatMoney(item.hidden_exposure);
    top.append(name, amount);
    const detail = document.createElement('div');
    detail.className = 'contribution-detail';
    detail.innerHTML = `<span>forecast gap ${formatMoney(item.deterministic_gap)}</span><span>pending ${formatMoney(item.pending_change)}</span><span>risk ${formatMoney(item.risk_exposure)}</span>`;
    card.append(bar, top, detail);
    card.addEventListener('click', () => inspectContribution(item));
    return card;
  });
  $('#contributionList').replaceChildren(...elements);

  const p = state.data.portfolio;
  const bridge = [
    ['Submitted reported EAC', p.reported_eac, ''],
    ['Forecast contradictions', p.deterministic_gap, '+'],
    ['Pending change + quantified risk', p.quantified_change_and_risk, '+'],
    ['Defensible risk-adjusted position', p.defensible_p80, '='],
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
    blocker.textContent = item.blockers ? `${item.blockers} blocker${item.blockers === 1 ? '' : 's'}` : 'review exception';
    card.append(name, count, blocker);
    return card;
  });
  $('#domainGrid').replaceChildren(...cards);
}

function renderExceptions() {
  const rows = (state.data.exceptions || []).map((item) => {
    const row = document.createElement('tr');
    const severity = document.createElement('td');
    const severityPill = document.createElement('span');
    severityPill.className = `severity ${['blocker', 'major', 'minor', 'info'].includes(item.severity) ? item.severity : 'major'}`;
    severityPill.textContent = item.severity;
    severity.append(severityPill);
    const record = document.createElement('td'); record.textContent = item.record_id;
    const title = document.createElement('td');
    const strong = document.createElement('strong'); strong.textContent = item.title;
    const code = document.createElement('div'); code.className = 'equation-meta'; code.textContent = item.equation_id;
    title.append(strong, code);
    const residual = document.createElement('td'); residual.textContent = formatResidual(item.residual);
    const impact = document.createElement('td'); impact.textContent = item.impact_metric.replaceAll('_', ' ');
    const action = document.createElement('td'); action.textContent = item.remediation;
    row.append(severity, record, title, residual, impact, action);
    row.addEventListener('click', () => inspectFinding(item));
    return row;
  });
  $('#exceptionRows').replaceChildren(...rows);
}
