function renderCatalogue() {
  const enabled = new Set(state.catalogue.map((item) => item.id));
  $('#equationCount').textContent = `${state.catalogue.length} tested controls`;
  const cards = state.catalogue.map((item) => {
    const label = document.createElement('label');
    label.className = 'equation-card';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = enabled.has(item.id);
    checkbox.dataset.equationId = item.id;
    const copy = document.createElement('span');
    const meta = document.createElement('span'); meta.className = 'equation-meta'; meta.textContent = `${item.domain} · ${item.severity} · ${item.record_type.replace('_', ' ')}`;
    const title = document.createElement('strong'); title.textContent = item.title;
    const code = document.createElement('code'); code.textContent = item.expression;
    copy.append(meta, title, code);
    label.append(checkbox, copy);
    return label;
  });
  $('#catalogueGrid').replaceChildren(...cards);
}

function renderCustomEquations() {
  const chips = state.customEquations.map((item, index) => {
    const chip = document.createElement('div'); chip.className = 'custom-chip';
    const copy = document.createElement('span'); copy.textContent = `${item.title}: ${item.expression}`;
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'remove';
    remove.addEventListener('click', () => { state.customEquations.splice(index, 1); renderCustomEquations(); });
    chip.append(copy, remove);
    return chip;
  });
  $('#customEquationList').replaceChildren(...chips);
}

function inspectContribution(item) {
  openInspector('Control account reconstruction', String(item.record_id), `
    <dl>
      <dt>Reported EAC</dt><dd>${formatMoney(item.reported_eac)}</dd>
      <dt>Defensible EAC</dt><dd>${formatMoney(item.defensible_eac)}</dd>
      <dt>Forecast contradiction</dt><dd>${formatMoney(item.deterministic_gap)}</dd>
      <dt>Pending change</dt><dd>${formatMoney(item.pending_change)}</dd>
      <dt>Quantified risk</dt><dd>${formatMoney(item.risk_exposure)}</dd>
      <dt>Defensible P80</dt><dd>${formatMoney(item.defensible_p80)}</dd>
      <dt>Hidden exposure</dt><dd>${formatMoney(item.hidden_exposure)}</dd>
    </dl>
    <div class="inspector-action"><strong>Why this matters</strong><br>The account's reported forecast is compared with governed AC + ETC, then pending change and quantified risk are layered onto the reconstructed position.</div>
  `);
}

function inspectFinding(item) {
  openInspector(item.domain.replaceAll('_', ' '), String(item.title), `
    <dl>
      <dt>Record</dt><dd>${escapeHtml(item.record_id)}</dd>
      <dt>Severity</dt><dd>${escapeHtml(item.severity)}</dd>
      <dt>Residual</dt><dd>${formatResidual(item.residual)}</dd>
      <dt>Executive impact</dt><dd>${escapeHtml(item.impact_metric.replaceAll('_', ' '))}</dd>
    </dl>
    <code>${escapeHtml(item.expression)}</code>
    <p>${escapeHtml(item.description)}</p>
    <div class="inspector-action"><strong>Required action</strong><br>${escapeHtml(item.remediation)}</div>
  `);
}

function inspectMetric(metric) {
  const p = state.data.portfolio;
  const descriptions = {
    reported_eac: ['Reported EAC', 'The sum of submitted EAC values. This is the position currently visible in the close package.', p.reported_eac],
    defensible_eac: ['Defensible EAC', 'The sum of AC + ETC wherever both governed components are available. This exposes forecast summaries that disagree with their own detail.', p.defensible_eac],
    defensible_p80: ['Defensible P80', 'Defensible EAC plus pending change and quantified risk exposure. It is reconstructed independently of the submitted P80 summary.', p.defensible_p80],
    hidden_exposure: ['Hidden exposure', 'The difference between the reconstructed risk-adjusted position and reported EAC—the amount not visible in the headline deterministic forecast.', p.hidden_exposure],
  };
  const [title, description, value] = descriptions[metric];
  openInspector('Executive metric', title, `<p>${description}</p><div class="inspector-action"><strong>${formatMoney(value)}</strong><br>Click an account contribution or evidence node to trace the amount back to its source.</div>`);
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
  const nodes = graph.nodes;
  const accountNodes = nodes.filter((item) => item.kind === 'account' || item.kind === 'activity');
  const findingNodes = nodes.filter((item) => item.kind === 'finding');
  const metricNodes = nodes.filter((item) => item.kind === 'metric' || item.kind === 'decision');
  const height = Math.max(500, Math.max(accountNodes.length, findingNodes.length, metricNodes.length) * 82 + 70);
  svg.setAttribute('viewBox', `0 0 1080 ${height}`);
  svg.style.height = `${height}px`;

  const positions = new Map();
  const place = (items, x) => items.forEach((item, index) => positions.set(item.id, { x, y: 45 + index * 82, width: item.kind === 'finding' ? 260 : 190, height: 50 }));
  place(accountNodes, 65); place(findingNodes, 395); place(metricNodes, 825);

  const ns = 'http://www.w3.org/2000/svg';
  for (const edge of graph.edges) {
    const source = positions.get(edge.source); const target = positions.get(edge.target);
    if (!source || !target) continue;
    const path = document.createElementNS(ns, 'path');
    const x1 = source.x + source.width; const y1 = source.y + source.height / 2;
    const x2 = target.x; const y2 = target.y + target.height / 2;
    const bend = Math.max(50, (x2 - x1) * .45);
    path.setAttribute('d', `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`);
    path.setAttribute('class', `graph-edge${edge.relation === 'impacts' || edge.relation === 'exposes' ? ' hot' : ''}`);
    svg.append(path);
  }

  for (const node of nodes) {
    const pos = positions.get(node.id); if (!pos) continue;
    const group = document.createElementNS(ns, 'g');
    group.setAttribute('class', `graph-node ${node.kind}`);
    group.setAttribute('transform', `translate(${pos.x} ${pos.y})`);
    const rect = document.createElementNS(ns, 'rect');
    rect.setAttribute('width', pos.width); rect.setAttribute('height', pos.height);
    const title = document.createElementNS(ns, 'text');
    title.setAttribute('x', 12); title.setAttribute('y', 21);
    title.textContent = node.label.length > 32 ? `${node.label.slice(0, 31)}…` : node.label;
    const meta = document.createElementNS(ns, 'text');
    meta.setAttribute('x', 12); meta.setAttribute('y', 38); meta.setAttribute('class', 'node-meta');
    meta.textContent = node.kind === 'finding' ? `${node.severity} · ${node.equation_id}` : node.kind;
    group.append(rect, title, meta);
    group.addEventListener('click', () => inspectGraphNode(node));
    svg.append(group);
  }
}

function inspectGraphNode(node) {
  if (node.kind === 'finding') {
    const finding = state.data.exceptions.find((item) => item.equation_id === node.equation_id && item.record_id === node.record_id);
    if (finding) return inspectFinding(finding);
  }
  if (node.kind === 'account' || node.kind === 'activity') {
    const contribution = state.data.surprise.contributions.find((item) => item.record_id === node.label);
    if (contribution) return inspectContribution(contribution);
  }
  const metricMap = { 'metric:reported': 'reported_eac', 'metric:defensible': 'defensible_eac', 'metric:risk': 'defensible_p80', 'metric:hidden': 'hidden_exposure' };
  if (metricMap[node.id]) inspectMetric(metricMap[node.id]);
}
