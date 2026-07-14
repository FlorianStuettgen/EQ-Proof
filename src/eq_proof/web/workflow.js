'use strict';

function buildEquationCandidate() {
  const expression = $('#customExpression').value.trim();
  const rawFields = $('#customFields').value.split(',').map((item) => item.trim()).filter(Boolean);
  const comparisons = expression.match(/==|<=|>=|<|>/g) || [];
  if (comparisons.length !== 1 || !rawFields.length) {
    throw new Error('Add exactly one comparison and at least one required field.');
  }
  if (expression.length > 512 || /[\r\n;]/.test(expression)) {
    throw new Error('Keep the equation on one line, under 512 characters, without statement separators.');
  }
  const invalidField = rawFields.find((field) => !/^[A-Za-z_][A-Za-z0-9_]*$/.test(field));
  if (invalidField) {
    throw new Error(`Required field “${invalidField}” is not a valid identifier.`);
  }
  const fields = [...new Set(rawFields)];
  const title = $('#customTitle').value.trim() || 'Custom control';
  const base = title.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'equation';
  const existing = new Set(state.customEquations.map((item) => item.id));
  let suffix = 1;
  let id = `custom.${base}_${suffix}`;
  while (existing.has(id)) { suffix += 1; id = `custom.${base}_${suffix}`; }
  return {
    id,
    title,
    domain: 'custom',
    expression,
    severity: $('#customSeverity').value,
    description: 'User-authored project control.',
    remediation: $('#customRemediation').value.trim() || 'Review the source data and equation.',
    required_fields: fields,
    record_type: $('#customRecordType').value,
  };
}

async function addCustomEquation() {
  try {
    const candidate = buildEquationCandidate();
    if (state.apiAvailable) {
      await fetchJson('./api/equations/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(candidate),
      });
    }
    state.customEquations.push(candidate);
    $('#editorStatus').textContent = state.apiAvailable
      ? `${candidate.title} validated by the local engine and added to the next analysis.`
      : `${candidate.title} passed browser structural checks and was added to the draft pack. Run the local app for authoritative engine validation.`;
    renderCustomEquations();
  } catch (error) {
    $('#editorStatus').textContent = error.message;
  }
}

function selectedCatalogueIds() {
  return [...(state.selectedCatalogueIds || new Set())];
}

function updateSelectedFiles() {
  const files = [...$('#p6Input').files, ...$('#costInput').files, ...$('#equationInput').files];
  $('#selectedFiles').textContent = files.length
    ? files.map((file) => `${file.name} · ${(file.size / 1024).toFixed(1)} KiB`).join('  |  ')
    : 'No files selected.';
}

async function compileClose(event) {
  event.preventDefault();
  if (!state.apiAvailable) {
    $('#apiStatus').textContent = "Real-file mode requires the local app: pip install -e '.[web]' && eq-controls serve";
    return;
  }
  const p6Files = [...$('#p6Input').files];
  const costFiles = [...$('#costInput').files];
  if (!p6Files.length && !costFiles.length) {
    $('#apiStatus').textContent = 'Select at least one P6 XER or cost CSV export.';
    return;
  }
  const form = new FormData();
  p6Files.forEach((file) => form.append('p6_xer', file));
  costFiles.forEach((file) => form.append('cost_csv', file));
  [...$('#equationInput').files].forEach((file) => form.append('equation_pack', file));
  form.append('custom_equations', JSON.stringify(state.customEquations));
  form.append('catalogue_ids', selectedCatalogueIds().join(','));
  const currency = $('#currencyInput').value.trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(currency)) { $('#apiStatus').textContent = 'Enter a three-letter currency code such as USD or CAD.'; return; }
  form.append('currency', currency);
  $('#compileButton').disabled = true;
  $('#compileButton').textContent = 'Compiling evidence…';
  $('#apiStatus').textContent = 'Hashing sources, executing equations, and reconstructing declared states…';
  $('#gateCard').setAttribute('aria-busy', 'true');
  try {
    const payload = await fetchJson('./api/analyze', { method: 'POST', body: form });
    state.data = payload;
    $('#workspaceTitle').textContent = 'Uploaded monthly close';
    renderAll();
    $('#uploadDialog').close();
    $('#workspace').scrollIntoView({ behavior: 'smooth' });
  } catch (error) {
    $('#apiStatus').textContent = error.message;
  } finally {
    $('#compileButton').disabled = false;
    $('#compileButton').textContent = 'Compile close';
    $('#gateCard').setAttribute('aria-busy', 'false');
  }
}

function downloadBlob(content, type, filename) {
  const blob = new Blob([content], { type });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportExceptions() {
  const headers = ['severity', 'record_type', 'record_id', 'equation_id', 'title', 'residual', 'residual_state', 'impact_metric', 'remediation'];
  const rows = [headers.join(','), ...(state.data.exceptions || []).map((item) => headers.map((key) => csvCell(item[key])).join(','))];
  downloadBlob(`\ufeff${rows.join('\n')}\n`, 'text/csv;charset=utf-8', 'eq-proof-exceptions.csv');
}

function exportEquationPack() {
  if (!state.customEquations.length) {
    $('#editorStatus').textContent = 'Add at least one custom equation before downloading a pack.';
    return;
  }
  downloadBlob(`${JSON.stringify(state.customEquations, null, 2)}\n`, 'application/json', 'eq-proof-equations.json');
  $('#editorStatus').textContent = `Downloaded ${state.customEquations.length} equation${state.customEquations.length === 1 ? '' : 's'}.`;
}

function activateTab(name) {
  $$('.tab').forEach((button) => {
    const active = button.dataset.tab === name;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
    button.tabIndex = active ? 0 : -1;
  });
  $$('.tab-panel').forEach((panel) => {
    const active = panel.id === `panel-${name}`;
    panel.classList.toggle('active', active);
    panel.hidden = !active;
  });
  if (name === 'graph') renderGraph();
}

function openUpload() {
  const dialog = $('#uploadDialog');
  if (!dialog.open) dialog.showModal();
  setRuntimeMode();
}

function updateExceptionFilters() {
  state.exceptionFilters.search = $('#exceptionSearch').value.trim();
  state.exceptionFilters.severity = $('#exceptionSeverity').value;
  state.exceptionFilters.domain = $('#exceptionDomain').value;
  renderExceptions();
}

async function init() {
  await Promise.all([detectApi(), loadDemo()]);
  $('#gateCard').setAttribute('aria-busy', 'false');
  $('#runDemoButton').addEventListener('click', () => $('#workspace').scrollIntoView({ behavior: 'smooth' }));
  ['#uploadButton', '#heroUploadButton'].forEach((selector) => $(selector).addEventListener('click', openUpload));
  $('#catalogueButton').addEventListener('click', () => { activateTab('equations'); $('#workspace').scrollIntoView({ behavior: 'smooth' }); });
  $$('.tab').forEach((button) => button.addEventListener('click', () => activateTab(button.dataset.tab)));
  $$('.info-button').forEach((button) => button.addEventListener('click', () => inspectMetric(button.dataset.inspect)));
  $('#inspectorClose').addEventListener('click', closeInspector);
  $('#dialogClose').addEventListener('click', () => $('#uploadDialog').close('cancel'));
  $('#addEquationButton').addEventListener('click', addCustomEquation);
  $('#downloadEquationPack').addEventListener('click', exportEquationPack);
  $('#analysisForm').addEventListener('submit', compileClose);
  ['#p6Input', '#costInput', '#equationInput'].forEach((selector) => $(selector).addEventListener('change', updateSelectedFiles));
  ['#exceptionSearch', '#exceptionSeverity', '#exceptionDomain'].forEach((selector) => $(selector).addEventListener('input', updateExceptionFilters));
  $('#downloadExceptions').addEventListener('click', exportExceptions);
}

init().then(() => {
  const showcase = document.createElement('script');
  showcase.src = './showcase.js';
  showcase.onerror = () => {
    $('#gateHeadline').textContent = 'The core analysis loaded, but the guided showcase failed to initialize.';
  };
  document.head.append(showcase);
}).catch((error) => {
  $('#gateCard').setAttribute('aria-busy', 'false');
  $('#gateHeadline').textContent = `Unable to load the control room: ${error.message}`;
});
