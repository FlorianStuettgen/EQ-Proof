'use strict';

function renderCatalogue() {
  if (state.selectedCatalogueIds === null) {
    state.selectedCatalogueIds = new Set(
      state.catalogue.map((item) => item.id),
    );
  }
  $('#equationCount').textContent = `${state.catalogue.length} tested controls`;
  const cards = state.catalogue.map((item) => {
    const label = document.createElement('label');
    label.className = 'equation-card';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = state.selectedCatalogueIds.has(item.id);
    checkbox.dataset.equationId = item.id;
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

function renderCustomEquations() {
  const chips = state.customEquations.map((item, index) => {
    const chip = document.createElement('div');
    chip.className = 'custom-chip';
    const copy = document.createElement('span');
    copy.textContent = `${item.title}: ${item.expression}`;
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'remove';
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
      <dt>Defensible EAC</dt><dd>${formatMoney(item.defensible_eac)}</dd>
      <dt>Deterministic forecast gap</dt><dd>${formatMoney(deterministic)}</dd>
      <dt>Pending change</dt><dd>${formatMoney(item.pending_change)}</dd>
      <dt>Configured risk uplift</dt><dd>${formatMoney(risk)}</dd>
      <dt>Submitted risk-adjusted summary</dt><dd>${formatMoney(submitted)}</dd>
      <dt>Reconstructed risk-adjusted position</dt><dd>${formatMoney(reconstructed)}</dd>
      <dt>Risk-adjusted reconciliation gap</dt><dd>${formatMoney(reconciliation)}</dd>
      <dt>Exposure above reported EAC</dt><dd>${formatMoney(exposure)}</dd>
    </dl>
    <div class="inspector-action"><strong>Interpretation boundary</strong><br>The risk-adjusted position applies declared pending change and configured risk uplift. It is not a Monte Carlo percentile unless the supplied risk field was produced by a governed probabilistic model.</div>
  `);
}

function inspectFinding(item) {
  openInspector(item.domain.replaceAll('_', ' '), String(item.title), `
    <dl>
      <dt>Record</dt><dd>${escapeHtml(item.record_id)}</dd>
      <dt>Severity</dt><dd>${escapeHtml(item.severity)}</dd>
      <dt>Residual</dt><dd>${formatResidual(item.residual, item.residual_state)}</dd>
      <dt>Declared impact</dt><dd>${escapeHtml(String(item.impact_metric || 'close_gate').replaceAll('_', ' '))}</dd>
    </dl>
    <code>${escapeHtml(item.expression)}</code>
    <p>${escapeHtml(item.description)}</p>
    <div class="inspector-action"><strong>Required action</strong><br>${escapeHtml(item.remediation)}</div>
  `);
}

function inspectMetric(metric) {
  const p = state.data.portfolio;
  const descriptions = {
    reported_eac: [
      'Reported EAC',
      'The sum of submitted EAC values. This is the deterministic position visible in the close package.',
      p.reported_eac,
    ],
    defensible_eac: [
      'Defensible EAC',
      'The sum of AC + ETC wherever both governed components are available. This exposes forecast summaries that disagree with their own detail.',
      p.defensible_eac,
    ],
    deterministic_forecast_gap: [
      'Deterministic forecast gap',
      'Defensible EAC minus reported EAC. This isolates internal forecast contradiction without mixing in pending change or risk.',
      p.deterministic_forecast_gap ?? p.deterministic_gap,
    ],
    risk_adjusted_position: [
      'Risk-adjusted position',
      'Defensible EAC plus declared pending change and configured risk uplift. This is an equation-derived bridge, not a probabilistic simulation.',
      p.reconstructed_risk_adjusted_eac ?? p.defensible_p80,
    ],
  };
  const definition = descriptions[metric];
  if (!definition) return;
  const [title, description, value] = definition;
  openInspector(
    'Executive metric',
    title,
    `<p>${description}</p><div class="inspector-action"><strong>${formatMoney(value)}</strong><br>Click an account contribution or evidence node to trace the value to declared source fields and equations.</div>`,
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
    const group = document.createElementNS(ns, 'g');
    group.setAttribute('class', `graph-node ${node.kind}`);
    group.setAttribute('transform', `translate(${pos.x} ${pos.y})`);
    group.setAttribute('tabindex', '0');
    group.setAttribute('role', 'button');
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('width', pos.width);
    rect.setAttribute('height', pos.height);
    const title = document.createElementNS(ns, 'text');
    title.setAttribute('x', 12);
    title.setAttribute('y', 21);
    title.textContent = node.label.length > 34
      ? `${node.label.slice(0, 33)}…`
      : node.label;
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
      if (event.key === 'Enter' || event.key === ' ') inspect();
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
