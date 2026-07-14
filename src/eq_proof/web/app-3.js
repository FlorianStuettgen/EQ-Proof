function addCustomEquation() {
  const expression = $('#customExpression').value.trim();
  const fields = $('#customFields').value.split(',').map((item) => item.trim()).filter(Boolean);
  if (!expression.match(/(==|<=|>=|<|>)/) || !fields.length) {
    $('#editorStatus').textContent = 'Add one comparison and at least one required field.';
    return;
  }
  const title = $('#customTitle').value.trim() || 'Custom control';
  const id = `custom.${title.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'equation'}_${state.customEquations.length + 1}`;
  state.customEquations.push({
    id, title, domain: 'custom', expression,
    severity: $('#customSeverity').value,
    description: 'User-authored project control.',
    remediation: $('#customRemediation').value.trim() || 'Review the source data and equation.',
    required_fields: fields,
    record_type: $('#customRecordType').value,
  });
  $('#editorStatus').textContent = `${title} added to the next analysis.`;
  renderCustomEquations();
}

function selectedCatalogueIds() {
  return $$('#catalogueGrid input[type="checkbox"]:checked').map((item) => item.dataset.equationId);
}

function updateSelectedFiles() {
  const files = [...$('#p6Input').files, ...$('#costInput').files, ...$('#equationInput').files];
  $('#selectedFiles').textContent = files.length ? files.map((file) => `${file.name} · ${(file.size / 1024).toFixed(1)} KiB`).join('  |  ') : 'No files selected.';
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
  $('#compileButton').disabled = true;
  $('#compileButton').textContent = 'Compiling evidence…';
  $('#apiStatus').textContent = 'Parsing sources, executing equations, reconstructing portfolio…';
  try {
    const response = await fetch('./api/analyze', { method: 'POST', body: form });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Analysis failed');
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
  }
}

function exportExceptions() {
  const headers = ['severity', 'record_type', 'record_id', 'equation_id', 'title', 'residual', 'impact_metric', 'remediation'];
  const rows = [headers.join(','), ...(state.data.exceptions || []).map((item) => headers.map((key) => escapeCsv(item[key])).join(','))];
  const blob = new Blob([`${rows.join('\n')}\n`], { type: 'text/csv' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob); link.download = 'eq-proof-exceptions.csv'; link.click();
  URL.revokeObjectURL(link.href);
}

function activateTab(name) {
  $$('.tab').forEach((button) => button.classList.toggle('active', button.dataset.tab === name));
  $$('.tab-panel').forEach((panel) => panel.classList.toggle('active', panel.id === `panel-${name}`));
  if (name === 'graph') renderGraph();
}

function openUpload() {
  $('#uploadDialog').showModal();
}

async function init() {
  await Promise.all([detectApi(), loadDemo()]);
  $('#runDemoButton').addEventListener('click', () => $('#workspace').scrollIntoView({ behavior: 'smooth' }));
  ['#uploadButton', '#heroUploadButton'].forEach((selector) => $(selector).addEventListener('click', openUpload));
  $('#catalogueButton').addEventListener('click', () => { activateTab('equations'); $('#workspace').scrollIntoView({ behavior: 'smooth' }); });
  $$('.tab').forEach((button) => button.addEventListener('click', () => activateTab(button.dataset.tab)));
  $$('.info-button').forEach((button) => button.addEventListener('click', () => inspectMetric(button.dataset.inspect)));
  $('#inspectorClose').addEventListener('click', closeInspector);
  $('#addEquationButton').addEventListener('click', addCustomEquation);
  $('#analysisForm').addEventListener('submit', compileClose);
  ['#p6Input', '#costInput', '#equationInput'].forEach((selector) => $(selector).addEventListener('change', updateSelectedFiles));
  $('#downloadExceptions').addEventListener('click', exportExceptions);
}

init().catch((error) => {
  $('#gateHeadline').textContent = `Unable to load the control room: ${error.message}`;
});
