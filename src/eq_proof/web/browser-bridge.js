'use strict';

(() => {
  const isStaticHost = window.location.hostname.endsWith('.github.io')
    || window.location.port === '4173';
  if (!isStaticHost) return;

  const WORKSPACE_KEY = 'eq-proof/browser-workspace@1';
  const PERSISTENCE_KEY = 'eq-proof/browser-persistence@1';

  window.EQ_PROOF_BROWSER_MODE = true;

  function persistenceEnabled() {
    try {
      return window.localStorage.getItem(PERSISTENCE_KEY) === 'enabled';
    } catch (error) {
      console.warn('EQ-Proof could not read the browser persistence preference:', error);
      return false;
    }
  }

  function setPersistencePreference(enabled) {
    try {
      if (enabled) window.localStorage.setItem(PERSISTENCE_KEY, 'enabled');
      else window.localStorage.removeItem(PERSISTENCE_KEY);
    } catch (error) {
      console.warn('EQ-Proof could not update the browser persistence preference:', error);
    }
  }

  async function runWithWorkspaceWritePolicy(callback) {
    if (persistenceEnabled()) return callback();
    const storagePrototype = Object.getPrototypeOf(window.localStorage);
    const originalSetItem = storagePrototype.setItem;
    storagePrototype.setItem = function guardedSetItem(key, value) {
      if (this === window.localStorage && key === WORKSPACE_KEY) return undefined;
      return originalSetItem.call(this, key, value);
    };
    try {
      return await callback();
    } finally {
      storagePrototype.setItem = originalSetItem;
    }
  }

  function markPersistence(payload, persisted) {
    if (!payload || typeof payload !== 'object') return payload;
    payload.runtime = {
      ...(payload.runtime || {}),
      engine: 'browser',
      data_left_device: false,
      persisted_locally: persisted,
    };
    return payload;
  }

  function retainSessionOnly(engine, payload) {
    markPersistence(payload, false);
    engine.clearWorkspace();
    engine.setCurrentPayload(payload, false);
    return payload;
  }

  function persistWorkspace(engine, payload) {
    markPersistence(payload, true);
    engine.setCurrentPayload(payload, true);
    return payload;
  }

  function updateAssuranceCopy() {
    const metricLabel = document.querySelector('[data-inspect="defensible_eac"]')?.closest('.metric-label');
    if (metricLabel) {
      const textNode = [...metricLabel.childNodes].find((node) => node.nodeType === Node.TEXT_NODE);
      if (textNode) textNode.textContent = 'Detail-reconstructed EAC ';
    }
    document.querySelector('[data-inspect="defensible_eac"]')?.setAttribute('aria-label', 'Explain detail-reconstructed EAC');
    const assuranceLabel = document.querySelector('#assuranceRing small');
    if (assuranceLabel) assuranceLabel.textContent = 'severity index';
    const assuranceNote = document.getElementById('assuranceNote');
    if (assuranceNote) {
      assuranceNote.textContent = 'The control severity index is a transparent finding-weight heuristic, not a probability or calibrated assurance measure.';
      if (state.data?.analysis?.equations_executed === 0) {
        assuranceNote.textContent = `No controls executed; ${state.data.analysis.summary?.not_applicable ?? 0} checks were not applicable. A ready gate does not establish forecast reconciliation.`;
      }
    }
  }

  async function installShowcaseCases(engine, compile, isCompiling) {
    const section = document.createElement('section');
    section.className = 'showcase-cases';
    section.id = 'showcaseCases';
    section.setAttribute('aria-labelledby', 'showcaseCasesTitle');
    section.innerHTML = `
      <h3 id="showcaseCasesTitle">Try a complete example</h3>
      <p>Synthetic files, real analysis. Each example uses its included source files and controls, and replaces the active result. Export your current analysis first if you need to keep it.</p>
      <div class="showcase-case-controls">
        <label for="showcaseCaseSelect">Example case<select id="showcaseCaseSelect" disabled><option>Loading examples…</option></select></label>
        <button class="button button-secondary" id="runShowcaseCase" type="button" disabled>Run example</button>
      </div>
      <p id="showcaseCaseDescription"></p>
      <div id="showcaseCaseSources" class="showcase-case-sources" aria-label="Example source files"></div>
      <p id="showcaseCaseStatus" role="status" aria-live="polite"></p>`;
    $('#analysisForm .dialog-heading').insertAdjacentElement('afterend', section);

    const launcher = document.createElement('button');
    launcher.className = 'button button-secondary';
    launcher.id = 'showcaseCasesButton';
    launcher.type = 'button';
    launcher.textContent = 'Showcase examples';
    launcher.disabled = true;
    $('#workspaceTourButton').insertAdjacentElement('beforebegin', launcher);
    let openedFromShowcase = false;
    launcher.addEventListener('click', () => {
      openedFromShowcase = true;
      $('#uploadDialog').showModal();
      $('#showcaseCaseSelect').focus();
    });
    $('#uploadDialog').addEventListener('close', () => {
      if (openedFromShowcase) queueMicrotask(() => launcher.focus());
      openedFromShowcase = false;
    });

    const select = $('#showcaseCaseSelect');
    const run = $('#runShowcaseCase');
    const status = $('#showcaseCaseStatus');
    try {
      const response = await fetch('./showcase-cases.json', { signal: AbortSignal.timeout(8000) });
      if (!response.ok) throw new Error('Examples could not be loaded. You can still analyze your own files below.');
      const bundle = await response.json();
      if (bundle.schema_version !== 'eq-proof/showcase-cases@1' || !Array.isArray(bundle.cases) || !bundle.cases.length) {
        throw new Error('The example catalogue is unavailable. You can still analyze your own files below.');
      }
      select.replaceChildren();
      bundle.cases.forEach((example) => {
        const option = document.createElement('option');
        option.value = example.id;
        option.textContent = example.title;
        select.append(option);
      });
      const selected = () => bundle.cases.find((example) => example.id === select.value);
      const describe = () => {
        const example = selected();
        $('#showcaseCaseDescription').textContent = `${example.description} ${example.boundary || ''}`.trim();
        const sources = $('#showcaseCaseSources');
        sources.replaceChildren();
        example.source_files.forEach((source) => {
          const download = document.createElement('button');
          download.type = 'button';
          download.className = 'showcase-source-download';
          download.textContent = `Download ${source.name}`;
          download.addEventListener('click', () => downloadBlob(source.content, 'text/plain;charset=utf-8', source.name));
          sources.append(download);
        });
        status.textContent = 'Runs the full built-in catalogue and this example’s equation pack. Draft controls and file selections are not included.';
      };
      section.dataset.ready = 'true';
      select.disabled = isCompiling();
      run.disabled = isCompiling();
      describe();
      select.addEventListener('change', describe);
      run.addEventListener('click', async () => {
        const example = selected();
        const form = new FormData();
        example.source_files.forEach((source) => form.append(source.kind, new File([source.content], source.name)));
        form.append('catalogue_ids', engine.catalogue.map((equation) => equation.id).join(','));
        form.append('custom_equations', '[]');
        form.append('currency', example.currency || 'USD');
        status.textContent = 'Parsing example source files and executing controls…';
        try {
          await compile(form, example);
          status.textContent = `${example.title} analyzed from its source files.`;
        } catch (error) {
          status.textContent = error.message;
        }
      });
    } catch (error) {
      select.replaceChildren(new Option('Examples unavailable', ''));
      status.textContent = ['TimeoutError', 'AbortError'].includes(error.name)
        ? 'Examples took too long to load. Reload to try again, or analyze your own files below.'
        : error.message;
    } finally {
      launcher.disabled = false;
    }
  }

  function installPersistenceControls(engine, legacyWorkspaceCleared) {
    const actions = document.querySelector('.browser-workbench-actions');
    if (!actions || document.getElementById('rememberWorkspaceInput')) return;

    const toggle = document.createElement('label');
    toggle.className = 'browser-persistence-toggle';
    toggle.innerHTML = '<input id="rememberWorkspaceInput" type="checkbox"> <span>Remember workspace on this browser</span>';
    actions.prepend(toggle);

    const clearButton = document.createElement('button');
    clearButton.className = 'button button-quiet';
    clearButton.id = 'clearLocalWorkspaceButton';
    clearButton.type = 'button';
    clearButton.textContent = 'Clear saved workspace';
    actions.append(clearButton);

    const checkbox = document.getElementById('rememberWorkspaceInput');
    const status = document.getElementById('browserWorkspaceStatus');
    checkbox.checked = persistenceEnabled();

    const currentPayload = () => engine.getCurrentPayload() || state.data;

    checkbox.addEventListener('change', () => {
      const payload = currentPayload();
      if (checkbox.checked) {
        setPersistencePreference(true);
        if (payload) {
          state.data = persistWorkspace(engine, payload);
          if (status) status.textContent = 'Workspace persistence enabled. The active Control Room JSON is stored in this browser until you clear it.';
        } else if (status) {
          status.textContent = 'Workspace persistence enabled. The next completed analysis will be stored in this browser.';
        }
        return;
      }

      setPersistencePreference(false);
      if (payload) state.data = retainSessionOnly(engine, payload);
      else engine.clearWorkspace();
      if (status) status.textContent = 'Session-only mode enabled. The active result remains open, but no Control Room workspace is stored after this tab closes.';
    });

    clearButton.addEventListener('click', () => {
      const payload = currentPayload();
      setPersistencePreference(false);
      checkbox.checked = false;
      if (payload) state.data = retainSessionOnly(engine, payload);
      else engine.clearWorkspace();
      if (status) status.textContent = 'Saved browser workspace and persistence preference cleared. The current page remains session-only.';
    });

    const originalOpenButton = document.getElementById('openAnalysisButton');
    const originalOpenInput = document.getElementById('openAnalysisInput');
    if (originalOpenButton && originalOpenInput) {
      const openButton = originalOpenButton.cloneNode(true);
      const openInput = originalOpenInput.cloneNode(true);
      originalOpenButton.replaceWith(openButton);
      originalOpenInput.replaceWith(openInput);

      openButton.addEventListener('click', () => openInput.click());
      openInput.addEventListener('change', async () => {
        const file = openInput.files?.[0];
        if (!file) return;
        try {
          const payload = JSON.parse(await file.text());
          state.data = persistenceEnabled()
            ? persistWorkspace(engine, payload)
            : retainSessionOnly(engine, payload);
          state.catalogue = state.data.catalogue || engine.catalogue;
          if (state.selectedCatalogueIds === null) {
            state.selectedCatalogueIds = new Set(state.catalogue.map((item) => item.id));
          }
          $('#workspaceTitle').textContent = persistenceEnabled()
            ? 'Opened and saved browser workspace'
            : 'Opened session-only browser workspace';
          renderAll();
          syncShowcaseSummary();
          updateAssuranceCopy();
          if (status) {
            status.textContent = persistenceEnabled()
              ? `${file.name} opened and stored in this browser.`
              : `${file.name} opened for this session only. Export it before closing the tab.`;
          }
        } catch (error) {
          if (status) status.textContent = error.message;
        } finally {
          openInput.value = '';
        }
      });
    }

    if (status) {
      if (legacyWorkspaceCleared) {
        status.textContent = 'A workspace saved by an earlier version was cleared because persistence now requires explicit opt-in. This session is not stored.';
      } else if (checkbox.checked) {
        status.textContent = 'Workspace persistence is enabled. Analysis stays on this device and remains in this browser until cleared.';
      } else {
        status.textContent = 'Session-only by default. Files stay on this device; enable Remember workspace only when this browser and device are appropriate for project data.';
      }
    }
  }

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

    let legacyWorkspaceCleared = false;
    let restored = null;
    if (persistenceEnabled()) {
      restored = engine.restoreWorkspace();
    } else {
      try {
        legacyWorkspaceCleared = window.localStorage.getItem(WORKSPACE_KEY) !== null;
        if (legacyWorkspaceCleared) window.localStorage.removeItem(WORKSPACE_KEY);
      } catch (error) {
        console.warn('EQ-Proof could not clear the legacy browser workspace:', error);
      }
    }

    if (restored) {
      state.data = markPersistence(restored, true);
      state.catalogue = restored.catalogue || engine.catalogue;
      if (state.selectedCatalogueIds === null) {
        state.selectedCatalogueIds = new Set(state.catalogue.map((item) => item.id));
      }
      $('#workspaceTitle').textContent = 'Restored browser workspace';
      renderAll();
      syncShowcaseSummary();
    } else if (state.data) {
      markPersistence(state.data, false);
      engine.setCurrentPayload(state.data, false);
    }

    state.apiAvailable = true;
    setRuntimeMode();
    engine.installBrowserUi();
    installPersistenceControls(engine, legacyWorkspaceCleared);
    updateAssuranceCopy();

    let analysisInProgress = false;
    async function compileBrowserForm(payloadForm, example = null) {
      if (analysisInProgress) throw new Error('Wait for the current analysis to finish.');
      analysisInProgress = true;
      $('#compileButton').disabled = true;
      $('#runShowcaseCase').disabled = true;
      $('#showcaseCaseSelect').disabled = true;
      $('#compileButton').textContent = 'Compiling evidence…';
      $('#apiStatus').textContent = 'Parsing files, hashing sources, executing equations and reconstructing the close…';
      $('#gateCard').setAttribute('aria-busy', 'true');
      try {
        const payload = await runWithWorkspaceWritePolicy(() => engine.analyzeForm(payloadForm));
        if (example) {
          payload.demo = { name: example.title, description: example.description, synthetic: true, showcase_case: example.id };
          state.selectedCatalogueIds = new Set(engine.catalogue.map((equation) => equation.id));
          state.exceptionFilters = { search: '', severity: 'all', domain: 'all' };
          $('#exceptionSearch').value = '';
          $('#exceptionSeverity').value = 'all';
          $('#exceptionDomain').value = 'all';
          closeTour();
          activateTab('overview');
        }
        state.data = persistenceEnabled()
          ? persistWorkspace(engine, payload)
          : retainSessionOnly(engine, payload);
        state.catalogue = payload.catalogue || engine.catalogue;
        $('#workspaceTitle').textContent = example ? `${example.title} · synthetic` : 'Browser-compiled monthly close';
        renderAll();
        syncShowcaseSummary();
        updateAssuranceCopy();
        $('#apiStatus').textContent = persistenceEnabled()
          ? 'Analysis complete. The result is stored in this browser and available for export.'
          : 'Analysis complete in session-only mode. Export the result before closing this tab if you need to retain it.';
        const workspaceStatus = document.getElementById('browserWorkspaceStatus');
        if (workspaceStatus) workspaceStatus.textContent = $('#apiStatus').textContent;
        $('#uploadDialog').close();
        $('#workspace').scrollIntoView({ behavior: 'smooth' });
      } finally {
        analysisInProgress = false;
        $('#compileButton').disabled = false;
        const casesUnavailable = $('#showcaseCases').dataset.ready !== 'true';
        $('#runShowcaseCase').disabled = casesUnavailable;
        $('#showcaseCaseSelect').disabled = casesUnavailable;
        $('#compileButton').textContent = 'Compile close';
        $('#gateCard').setAttribute('aria-busy', 'false');
      }
    }

    installShowcaseCases(engine, compileBrowserForm, () => analysisInProgress);

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

      try {
        await compileBrowserForm(payloadForm);
      } catch (error) {
        $('#apiStatus').textContent = error.message;
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
