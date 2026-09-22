'use strict';

function renderCatalogue() {
  renderControlCoverage();
  if (state.selectedCatalogueIds === null) {
    state.selectedCatalogueIds = new Set(
      state.catalogue.map((item) => item.id),
    );
  }
  $('#equationCount').textContent = `${state.catalogue.length} available controls`;
  const cards = state.catalogue.map((item) => {
    const label = document.createElement('label');
    label.className = 'equation-card';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = state.selectedCatalogueIds.has(item.id);
    checkbox.dataset.equationId = item.id;
    checkbox.setAttribute('aria-label', `Include ${item.id} in the next file analysis`);
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) state.selectedCatalogueIds.add(item.id);
      else state.selectedCatalogueIds.delete(item.id);
    });
    const copy = document.createElement('span');
    const applicability = item.applicability_field
      ? ` · when ${item.applicability_field} matches ${item.applicability_values.join('/')}`
      : '';
    const meta = document.createElement('span');
    meta.className = 'equation-meta';
    meta.textContent = `${item.domain} · ${item.severity} · ${item.record_type.replace('_', ' ')}${applicability}`;
    const title = document.createElement('strong');
    title.textContent = item.title;
    const code = document.createElement('code');
    code.textContent = item.expression;
    copy.append(meta, title, code);
    label.append(checkbox, copy);
    return label;
  });
  $('#catalogueGrid').replaceChildren(...cards);
}

function controlStatusLabel(status) {
  return { pass: 'Passed', fail: 'Failed', not_applicable: 'Not applicable' }[status] || 'Unknown';
}

function renderControlCoverage() {
  const panel = $('#panel-equations');
  if (!panel || !state.data) return;
  let section = $('#controlCoverage');
  if (!section) {
    section = document.createElement('section');
    section.id = 'controlCoverage';
    section.className = 'panel control-coverage';
    section.setAttribute('aria-labelledby', 'controlCoverageTitle');
    section.innerHTML = `
      <h3 id="controlCoverageTitle">Controls in this result</h3>
      <p id="controlCoverageSummary" role="status" aria-live="polite"></p>
      <p class="evidence-note">These results belong to the active analysis. The catalogue and draft controls below configure the next file analysis; they do not change this result.</p>
      <details id="controlCoverageDetails">
        <summary>Inspect a control result</summary>
        <div class="control-result-controls">
          <div class="control-result-field"><label for="controlStatusFilter">Result status</label><select id="controlStatusFilter"><option value="all">All results</option><option value="fail">Failed</option><option value="pass">Passed</option><option value="not_applicable">Not applicable</option></select></div>
          <div class="control-result-field"><label for="controlResultSelect">Control result</label><select id="controlResultSelect"></select></div>
          <button id="inspectControlResult" class="button button-secondary" type="button">Inspect selected result</button>
        </div>
        <p id="controlResultCount" class="evidence-note" role="status" aria-live="polite"></p>
      </details>`;
    panel.prepend(section);
  }
  const findings = state.data.analysis?.findings;
  const details = $('#controlCoverageDetails');
  if (!Array.isArray(findings)) {
    $('#controlCoverageSummary').textContent = 'Per-record control results are not included in this artifact. Analyze its source files to review passes, failures and applicability.';
    details.hidden = true;
    return;
  }
  const counts = Object.fromEntries(['pass', 'fail', 'not_applicable'].map((status) => [status, findings.filter((finding) => finding.status === status).length]));
  $('#controlCoverageSummary').textContent = `${counts.pass} passed · ${counts.fail} failed · ${counts.not_applicable} not applicable. ${state.data.analysis.equations_executed} checks executed across ${state.data.analysis.records_analyzed} records.`;
  details.hidden = findings.length === 0;
  const filter = $('#controlStatusFilter');
  const select = $('#controlResultSelect');
  const inspect = $('#inspectControlResult');
  const populate = () => {
    const visible = findings.map((finding, index) => ({ finding, index }))
      .filter(({ finding }) => filter.value === 'all' || finding.status === filter.value);
    select.replaceChildren(...visible.map(({ finding, index }) => new Option(
      `${finding.record_id} · ${finding.equation_id} · ${controlStatusLabel(finding.status)}`, String(index),
    )));
    select.disabled = visible.length === 0;
    inspect.disabled = visible.length === 0;
    if (!visible.length) select.append(new Option('No results with this status', ''));
    $('#controlResultCount').textContent = `${visible.length} of ${findings.length} recorded results. Not applicable means the equation was not executed; it does not establish a pass.`;
  };
  filter.onchange = populate;
  inspect.onclick = () => {
    const finding = findings[Number(select.value)];
    if (!select.disabled && finding) inspectFinding(finding);
  };
  populate();
}

function sourceValue(value) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString('en-US', { maximumSignificantDigits: 21 })
    : String(value ?? 'Not retained');
}

function renderCustomEquations() {
  const chips = state.customEquations.map((item, index) => {
    const chip = document.createElement('div');
    chip.className = 'custom-chip';
    const copy = document.createElement('span');
    copy.textContent = `${item.title}: ${item.expression}`;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'remove';
    remove.setAttribute('aria-label', `Remove ${item.title}`);
    remove.addEventListener('click', () => {
      state.customEquations.splice(index, 1);
      renderCustomEquations();
    });
    chip.append(copy, remove);
    return chip;
  });
  $('#customEquationList').replaceChildren(...chips);
}

function inspectContribution(item) {
  const identityChecks = (state.data.analysis?.findings || []).filter((finding) => finding.equation_id === 'cost.eac_identity'
    && finding.record_id === item.record_id && ['pass', 'fail'].includes(finding.status));
  const values = identityChecks.length === 1 ? identityChecks[0].values : null;
  const detailAvailable = Number.isFinite(values?.AC) && Number.isFinite(values?.ETC);
  const deterministic = item.deterministic_forecast_gap
    ?? item.deterministic_gap;
  const risk = item.configured_risk_uplift ?? item.risk_exposure;
  const submitted = item.submitted_risk_adjusted_eac
    ?? item.submitted_p80;
  const reconstructed = item.reconstructed_risk_adjusted_eac
    ?? item.defensible_p80;
  const reconciliation = item.risk_adjusted_reconciliation_gap;
  const exposure = item.exposure_above_reported_eac
    ?? item.hidden_exposure;
  openInspector('Control account reconstruction', String(item.record_id), `
    <dl>
      <dt>Source</dt><dd>${escapeHtml(item.source || 'uploaded data')}</dd>
      <dt>Reported EAC</dt><dd>${formatMoney(item.reported_eac)}</dd>
      <dt>Actual cost (AC)</dt><dd>${detailAvailable ? escapeHtml(sourceValue(values.AC)) : 'Not evidenced'}</dd>
      <dt>Estimate to complete (ETC)</dt><dd>${detailAvailable ? escapeHtml(sourceValue(values.ETC)) : 'Not evidenced'}</dd>
      <dt>Detail-reconstructed EAC</dt><dd>${detailAvailable ? formatMoney(item.defensible_eac) : 'Not evidenced'}</dd>
      <dt>Deterministic forecast gap</dt><dd>${detailAvailable ? formatMoney(deterministic) : 'Not evidenced'}</dd>
      <dt>Pending change</dt><dd>${formatMoney(item.pending_change)}</dd>
      <dt>Configured risk uplift</dt><dd>${formatMoney(risk)}</dd>
      <dt>Submitted risk-adjusted summary</dt><dd>${formatMoney(submitted)}</dd>
      <dt>Reconstructed risk-adjusted position</dt><dd>${detailAvailable ? formatMoney(reconstructed) : 'Not evidenced'}</dd>
      <dt>Risk-adjusted reconciliation gap</dt><dd>${detailAvailable ? formatMoney(reconciliation) : 'Not evidenced'}</dd>
      <dt>Exposure above reported EAC</dt><dd>${detailAvailable ? formatMoney(exposure) : 'Not evidenced'}</dd>
    </dl>
    <p class="evidence-note">${detailAvailable ? `AC and ETC are the numeric values used by the recorded cost.eac_identity check, in ${escapeHtml(state.data.units?.currency || 'the selected currency')}.` : 'A unique executed EAC identity with both AC and ETC is not retained for this record. Its detail reconstruction cannot be confirmed from this artifact.'}</p>
    <div class="inspector-action"><strong>Interpretation boundary</strong><br>The risk-adjusted position applies declared pending change and configured risk uplift. This arithmetic does not calculate or certify a Monte Carlo percentile or the methodology behind a supplied risk value.</div>
  `);
}

function inspectFinding(item) {
  const equation = state.data.analysis?.equations?.find((candidate) => candidate.id === item.equation_id);
  const values = Object.entries(item.values || {});
  const sourceValues = values.length
    ? `<dl class="source-values">${values.map(([field, value]) => `<dt>${escapeHtml(field)}</dt><dd>${escapeHtml(sourceValue(value))}</dd>`).join('')}</dl>`
    : '<p class="evidence-note">No evaluated input values are retained for this result.</p>';
  const applicability = item.status === 'not_applicable'
    ? '<div class="inspector-action"><strong>Not executed</strong><br>Required inputs may be absent or non-numeric, or the applicability condition may not match. This retained result does not distinguish those reasons. Not applicable is not a pass.</div>'
    : item.status === 'pass'
      ? '<div class="inspector-action"><strong>Passed within scope</strong><br>The retained values satisfy this equation under its configured tolerance. This is not source verification or management approval.</div>'
      : `<div class="inspector-action"><strong>Required action</strong><br>${escapeHtml(item.remediation)}</div>`;
  openInspector(item.domain.replaceAll('_', ' '), String(item.title), `
    <dl>
      <dt>Record</dt><dd>${escapeHtml(item.record_id)}</dd>
      <dt>Equation ID</dt><dd>${escapeHtml(item.equation_id)}</dd>
      <dt>Result</dt><dd>${escapeHtml(controlStatusLabel(item.status))}</dd>
      <dt>Severity</dt><dd>${escapeHtml(item.severity)}</dd>
      ${item.status !== 'not_applicable' ? `<dt>Residual</dt><dd>${formatResidual(item.residual, item.residual_state)}</dd>` : ''}
      ${item.impact_metric ? `<dt>Declared impact</dt><dd>${escapeHtml(String(item.impact_metric).replaceAll('_', ' '))}</dd>` : ''}
    </dl>
    <code>${escapeHtml(item.expression)}</code>
    <p>${escapeHtml(item.description)}</p>
    <h4>Values used by the control</h4>
    ${sourceValues}
    ${equation?.required_fields ? `<p class="evidence-note">Required fields: ${equation.required_fields.map(escapeHtml).join(', ')}.</p>` : ''}
    ${equation?.applicability_field ? `<p class="evidence-note">Applies when ${escapeHtml(equation.applicability_field)} matches ${equation.applicability_values.map(escapeHtml).join(', ')}.</p>` : ''}
    ${applicability}
  `);
}

function inspectMetric(metric) {
  const p = state.data.portfolio;
  const coverage = typeof forecastDetailAvailable === 'function' ? forecastDetailAvailable() : null;
  const reconstructionUnavailable = coverage === false
    && ['defensible_eac', 'deterministic_forecast_gap', 'risk_adjusted_position'].includes(metric);
  const descriptions = {
    reported_eac: [
      'Reported EAC',
      'The sum of submitted EAC values. This is the deterministic position visible in the close package.',
      p.reported_eac,
    ],
    defensible_eac: [
      'Detail-reconstructed EAC',
      'The sum of AC + ETC wherever both governed components are available. This exposes forecast summaries that disagree with their own detail.',
      p.defensible_eac,
    ],
    deterministic_forecast_gap: [
      'Deterministic forecast gap',
      'Detail-reconstructed EAC minus reported EAC. This isolates internal forecast contradiction without mixing in pending change or risk.',
      p.deterministic_forecast_gap ?? p.deterministic_gap,
    ],
    risk_adjusted_position: [
      'Risk-adjusted position',
      'Detail-reconstructed EAC plus declared pending change and configured risk uplift. This is an equation-derived bridge, not a probabilistic simulation.',
      p.reconstructed_risk_adjusted_eac ?? p.defensible_p80,
    ],
  };
  const definition = descriptions[metric];
  if (!definition) return;
  const [title, description, value] = definition;
  openInspector(
    'Executive metric',
    title,
    `<p>${reconstructionUnavailable ? 'The executed controls do not establish complete AC + ETC coverage. Inspect the recorded results and source fields before relying on forecast reconciliation.' : description}</p><div class="inspector-action"><strong>${reconstructionUnavailable ? 'Unavailable — AC and ETC not evidenced' : formatMoney(value)}</strong><br>Click an account contribution or evidence node to trace the value to declared source fields and equations.</div>`,
  );
}

function openInspector(eyebrow, title, html) {
  $('#inspectorEyebrow').textContent = eyebrow;
  $('#inspectorTitle').textContent = title;
  $('#inspectorBody').innerHTML = html;
  $('#inspector').classList.add('open');
  $('#inspector').setAttribute('aria-hidden', 'false');
}

function closeInspector() {
  $('#inspector').classList.remove('open');
  $('#inspector').setAttribute('aria-hidden', 'true');
}

function renderGraph() {
  const svg = $('#evidenceGraph');
  svg.replaceChildren();
  const graph = state.data.graph;
  const nodes = graph.nodes || [];
  const accountNodes = nodes.filter(
    (item) => item.kind === 'account' || item.kind === 'activity',
  );
  const findingNodes = nodes.filter((item) => item.kind === 'finding');
  const impactNodes = nodes.filter(
    (item) => !['account', 'activity', 'finding'].includes(item.kind),
  );
  const height = Math.max(
    560,
    Math.max(
      accountNodes.length,
      findingNodes.length,
      impactNodes.length,
    ) * 82 + 70,
  );
  svg.setAttribute('viewBox', `0 0 1120 ${height}`);
  svg.style.height = `${height}px`;

  const positions = new Map();
  const place = (items, x) => items.forEach((item, index) => positions.set(
    item.id,
    {
      x,
      y: 45 + index * 82,
      width: item.kind === 'finding' ? 270 : 205,
      height: 50,
    },
  ));
  place(accountNodes, 55);
  place(findingNodes, 390);
  place(impactNodes, 840);

  const ns = 'http://www.w3.org/2000/svg';
  for (const edge of graph.edges || []) {
    const source = positions.get(edge.source);
    const target = positions.get(edge.target);
    if (!source || !target) continue;
    const path = document.createElementNS(ns, 'path');
    const x1 = source.x + source.width;
    const y1 = source.y + source.height / 2;
    const x2 = target.x;
    const y2 = target.y + target.height / 2;
    const bend = Math.max(50, (x2 - x1) * .45);
    path.setAttribute(
      'd',
      `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`,
    );
    path.setAttribute(
      'class',
      `graph-edge${['gates', 'affects', 'informs'].includes(edge.relation) ? ' hot' : ''}`,
    );
    svg.append(path);
  }

  for (const node of nodes) {
    const pos = positions.get(node.id);
    if (!pos) continue;
    const label = node.id === 'metric:defensible' ? 'Detail-reconstructed EAC' : node.label;
    const group = document.createElementNS(ns, 'g');
    group.setAttribute('class', `graph-node ${node.kind}`);
    group.setAttribute('transform', `translate(${pos.x} ${pos.y})`);
    group.setAttribute('tabindex', '0');
    group.setAttribute('role', 'button');
    group.setAttribute(
      'aria-label',
      `Inspect ${node.kind} node ${label}${node.equation_id ? `, ${node.equation_id}` : ''}`,
    );
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('width', pos.width);
    rect.setAttribute('height', pos.height);
    const title = document.createElementNS(ns, 'text');
    title.setAttribute('x', 12);
    title.setAttribute('y', 21);
    title.textContent = label.length > 34
      ? `${label.slice(0, 33)}…`
      : label;
    const meta = document.createElementNS(ns, 'text');
    meta.setAttribute('x', 12);
    meta.setAttribute('y', 38);
    meta.setAttribute('class', 'node-meta');
    meta.textContent = node.kind === 'finding'
      ? `${node.severity} · ${node.equation_id}`
      : node.kind;
    group.append(rect, title, meta);
    const inspect = () => inspectGraphNode(node);
    group.addEventListener('click', inspect);
    group.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        inspect();
      }
    });
    svg.append(group);
  }
  const limits = graph.limits;
  $('#graphLimitBadge').textContent = limits?.truncated
    ? `Top ${limits.findings_shown}/${limits.findings_total} findings`
    : 'Complete declared lineage';
}

function inspectGraphNode(node) {
  if (node.kind === 'finding') {
    const finding = state.data.exceptions.find(
      (item) => item.equation_id === node.equation_id
        && item.record_id === node.record_id,
    );
    if (finding) return inspectFinding(finding);
  }
  if (node.kind === 'account' || node.kind === 'activity') {
    const contribution = state.data.surprise.contributions.find(
      (item) => item.record_id === node.label,
    );
    if (contribution) return inspectContribution(contribution);
    return openInspector(
      node.kind,
      node.label,
      '<p>This record contributes an assurance finding but is not mapped to a monetary control-account reconstruction.</p>',
    );
  }
  const metricMap = {
    'metric:reported': 'reported_eac',
    'metric:defensible': 'defensible_eac',
    'metric:deterministic_gap': 'deterministic_forecast_gap',
    'metric:risk_adjusted': 'risk_adjusted_position',
  };
  if (metricMap[node.id]) return inspectMetric(metricMap[node.id]);
  return openInspector(
    node.kind,
    node.label,
    '<p>This node represents a declared assurance or gate impact. EQ-Proof does not assign a dollar value unless an explicit equation supplies one.</p>',
  );
}
