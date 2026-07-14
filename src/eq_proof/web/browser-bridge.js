'use strict';

(() => {
  const isStaticHost = window.location.hostname.endsWith('.github.io')
    || window.location.port === '4173';
  if (!isStaticHost) return;

  window.EQ_PROOF_BROWSER_MODE = true;

  const stylesheet = document.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = './browser-workbench.css';
  document.head.append(stylesheet);

  const engineScript = document.createElement('script');
  engineScript.src = './browser-engine.js';
  engineScript.onerror = () => {
    $('#gateHeadline').textContent = 'The browser analysis engine failed to load.';
  };
  engineScript.onload = () => {
    const engine = window.EQProofBrowser;
    if (!engine) return;

    const restored = engine.restoreWorkspace();
    if (restored) {
      state.data = restored;
      state.catalogue = restored.catalogue || engine.catalogue;
      if (state.selectedCatalogueIds === null) {
        state.selectedCatalogueIds = new Set(state.catalogue.map((item) => item.id));
      }
      $('#workspaceTitle').textContent = 'Restored browser workspace';
      renderAll();
      syncShowcaseSummary();
    } else if (state.data) {
      engine.setCurrentPayload(state.data, false);
    }

    state.apiAvailable = true;
    setRuntimeMode();
    engine.installBrowserUi();

    const form = $('#analysisForm');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      const p6Files = [...$('#p6Input').files];
      const costFiles = [...$('#costInput').files];
      if (!p6Files.length && !costFiles.length) {
        $('#apiStatus').textContent = 'Select at least one P6 XER or cost CSV export.';
        return;
      }
      const currency = $('#currencyInput').value.trim().toUpperCase();
      if (!/^[A-Z]{3}$/.test(currency)) {
        $('#apiStatus').textContent = 'Enter a three-letter currency code such as USD or CAD.';
        return;
      }
      const payloadForm = new FormData();
      p6Files.forEach((file) => payloadForm.append('p6_xer', file));
      costFiles.forEach((file) => payloadForm.append('cost_csv', file));
      [...$('#equationInput').files].forEach((file) => payloadForm.append('equation_pack', file));
      payloadForm.append('custom_equations', JSON.stringify(state.customEquations));
      payloadForm.append('catalogue_ids', [...(state.selectedCatalogueIds || new Set())].join(','));
      payloadForm.append('currency', currency);

      $('#compileButton').disabled = true;
      $('#compileButton').textContent = 'Compiling evidence…';
      $('#apiStatus').textContent = 'Parsing files, hashing sources, executing equations and reconstructing the close…';
      $('#gateCard').setAttribute('aria-busy', 'true');
      try {
        const payload = await engine.analyzeForm(payloadForm);
        state.data = payload;
        state.catalogue = payload.catalogue || engine.catalogue;
        $('#workspaceTitle').textContent = 'Browser-compiled monthly close';
        renderAll();
        syncShowcaseSummary();
        $('#apiStatus').textContent = 'Analysis complete. The result is saved in this browser and available for export.';
        $('#uploadDialog').close();
        $('#workspace').scrollIntoView({ behavior: 'smooth' });
      } catch (error) {
        $('#apiStatus').textContent = error.message;
      } finally {
        $('#compileButton').disabled = false;
        $('#compileButton').textContent = 'Compile close';
        $('#gateCard').setAttribute('aria-busy', 'false');
      }
    }, true);

    $('#addEquationButton').addEventListener('click', (event) => {
      event.preventDefault();
      event.stopImmediatePropagation();
      try {
        const candidate = engine.validateEquation(buildEquationCandidate());
        state.customEquations.push(candidate);
        $('#editorStatus').textContent = `${candidate.title} validated by the browser engine and added to the next analysis.`;
        renderCustomEquations();
      } catch (error) {
        $('#editorStatus').textContent = error.message;
      }
    }, true);
  };
  document.head.append(engineScript);
})();
