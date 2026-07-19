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
    const assuranceLabel = document.querySelector('#assuranceRing small');
    if (assuranceLabel) assuranceLabel.textContent = 'severity index';
    const assuranceNote = document.getElementById('assuranceNote');
    if (assuranceNote) {
      assuranceNote.textContent = 'The control severity index is a transparent finding-weight heuristic, not a probability or calibrated assurance measure.';
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
        state.data = persistenceEnabled()
          ? persistWorkspace(engine, payload)
          : retainSessionOnly(engine, payload);
        state.catalogue = payload.catalogue || engine.catalogue;
        $('#workspaceTitle').textContent = 'Browser-compiled monthly close';
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
