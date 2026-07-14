'use strict';

(() => {
  const all = (selector, root = document) => [...root.querySelectorAll(selector)];
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const isFormControl = (element) => element?.matches?.('input, textarea, select, [contenteditable="true"]');
  const focusIfAvailable = (element) => {
    if (element instanceof HTMLElement && document.contains(element) && !element.hasAttribute('disabled')) {
      element.focus({ preventScroll: true });
    }
  };

  if (reducedMotion.matches && !Element.prototype.scrollIntoView.__eqProofReducedMotion) {
    const nativeScrollIntoView = Element.prototype.scrollIntoView;
    const reducedScrollIntoView = function scrollIntoView(options) {
      if (options && typeof options === 'object' && options.behavior === 'smooth') {
        return nativeScrollIntoView.call(this, { ...options, behavior: 'auto' });
      }
      return nativeScrollIntoView.call(this, options);
    };
    reducedScrollIntoView.__eqProofReducedMotion = true;
    Element.prototype.scrollIntoView = reducedScrollIntoView;
  }

  function synchronizeTabs() {
    const tabs = all('.tab[role="tab"]');
    tabs.forEach((tab, index) => {
      const name = tab.dataset.tab;
      const panel = document.getElementById(`panel-${name}`);
      if (!panel) return;
      const selected = tab.classList.contains('active');
      tab.id ||= `tab-${name}`;
      tab.setAttribute('aria-controls', panel.id);
      tab.setAttribute('aria-selected', String(selected));
      tab.tabIndex = selected ? 0 : -1;
      panel.setAttribute('aria-labelledby', tab.id);
      panel.hidden = !selected;

      if (tab.dataset.keyboardReady === 'true') return;
      tab.dataset.keyboardReady = 'true';
      tab.addEventListener('keydown', (event) => {
        const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
        if (!keys.includes(event.key)) return;
        event.preventDefault();
        const currentIndex = tabs.indexOf(tab);
        let nextIndex = currentIndex;
        if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
        if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
        if (event.key === 'Home') nextIndex = 0;
        if (event.key === 'End') nextIndex = tabs.length - 1;
        const next = tabs[nextIndex];
        window.activateTab(next.dataset.tab);
        next.focus();
      });
    });
  }

  if (typeof window.activateTab === 'function' && !window.activateTab.__eqProofAudited) {
    const originalActivateTab = window.activateTab;
    const auditedActivateTab = function activateAuditedTab(name) {
      originalActivateTab(name);
      synchronizeTabs();
    };
    auditedActivateTab.__eqProofAudited = true;
    window.activateTab = auditedActivateTab;
  }
  synchronizeTabs();

  function makeKeyboardClickable(element, label) {
    if (element.dataset.keyboardClickable === 'true') return;
    element.dataset.keyboardClickable = 'true';
    element.tabIndex = 0;
    element.setAttribute('role', 'button');
    if (label && !element.getAttribute('aria-label')) element.setAttribute('aria-label', label);
    element.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter' && event.key !== ' ') return;
      event.preventDefault();
      element.click();
    });
  }

  function enhanceDynamicContent() {
    const contributionList = document.getElementById('contributionList');
    if (contributionList) {
      const contributions = all('.contribution', contributionList);
      contributions.forEach((card) => {
        const record = card.querySelector('.contribution-top strong')?.textContent?.trim() || 'control account';
        makeKeyboardClickable(card, `Inspect ${record} reconstruction`);
      });
      const existingEmpty = contributionList.querySelector('[data-empty-state="contributions"]');
      if (!contributions.length && !existingEmpty) {
        const empty = document.createElement('p');
        empty.className = 'empty-state';
        empty.dataset.emptyState = 'contributions';
        empty.textContent = 'No monetary control-account reconstruction is available for this data set.';
        contributionList.append(empty);
      } else if (contributions.length) {
        existingEmpty?.remove();
      }
    }

    const domainGrid = document.getElementById('domainGrid');
    if (domainGrid) {
      const domains = all('.domain-card', domainGrid);
      const existingEmpty = domainGrid.querySelector('[data-empty-state="domains"]');
      if (!domains.length && !existingEmpty) {
        const empty = document.createElement('p');
        empty.className = 'empty-state';
        empty.dataset.emptyState = 'domains';
        empty.textContent = 'No failed assurance domains were reported.';
        domainGrid.append(empty);
      } else if (domains.length) {
        existingEmpty?.remove();
      }
    }

    const exceptionRows = document.getElementById('exceptionRows');
    if (exceptionRows) {
      const rows = all('tr:not(.empty-row)', exceptionRows);
      rows.forEach((row) => {
        const cells = all('td', row).map((cell) => cell.textContent.trim()).filter(Boolean);
        makeKeyboardClickable(row, `Inspect exception: ${cells.slice(0, 3).join(', ')}`);
      });
      const existingEmpty = exceptionRows.querySelector('.empty-row');
      if (!rows.length && !existingEmpty) {
        const row = document.createElement('tr');
        row.className = 'empty-row';
        const cell = document.createElement('td');
        cell.colSpan = 6;
        cell.textContent = 'No exceptions match the current filters.';
        row.append(cell);
        exceptionRows.append(row);
      } else if (rows.length) {
        existingEmpty?.remove();
      }
    }

    all('.custom-chip button').forEach((button) => {
      const title = button.closest('.custom-chip')?.querySelector('span')?.textContent?.split(':')[0]?.trim();
      button.setAttribute('aria-label', `Remove ${title || 'custom equation'}`);
    });

    all('.graph-node[role="button"]').forEach((node) => {
      const text = all('text', node).map((item) => item.textContent.trim()).filter(Boolean).join(', ');
      if (text) node.setAttribute('aria-label', `Inspect evidence node: ${text}`);
      if (node.dataset.spaceGuard === 'true') return;
      node.dataset.spaceGuard = 'true';
      node.addEventListener('keydown', (event) => {
        if (event.key === ' ') event.preventDefault();
      }, true);
    });
  }

  const workspace = document.getElementById('workspace');
  if (workspace) {
    let queued = false;
    new MutationObserver(() => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(() => {
        queued = false;
        enhanceDynamicContent();
        synchronizeTabs();
      });
    }).observe(workspace, { childList: true, subtree: true });
  }
  enhanceDynamicContent();

  ['editorStatus', 'apiStatus', 'selectedFiles', 'exceptionFilterCount'].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;
    element.setAttribute('role', 'status');
    element.setAttribute('aria-live', 'polite');
    element.setAttribute('aria-atomic', 'true');
  });

  const inspector = document.getElementById('inspector');
  const inspectorClose = document.getElementById('inspectorClose');
  let inspectorReturnFocus = null;
  if (inspector) {
    inspector.setAttribute('inert', '');
    if (typeof window.openInspector === 'function' && !window.openInspector.__eqProofAudited) {
      const originalOpenInspector = window.openInspector;
      const auditedOpenInspector = function openAuditedInspector(...args) {
        inspectorReturnFocus = document.activeElement;
        inspector.removeAttribute('inert');
        originalOpenInspector(...args);
        requestAnimationFrame(() => focusIfAvailable(inspectorClose));
      };
      auditedOpenInspector.__eqProofAudited = true;
      window.openInspector = auditedOpenInspector;
    }
    if (typeof window.closeInspector === 'function' && !window.closeInspector.__eqProofAudited) {
      const originalCloseInspector = window.closeInspector;
      const auditedCloseInspector = function closeAuditedInspector(...args) {
        originalCloseInspector(...args);
        inspector.setAttribute('inert', '');
        queueMicrotask(() => focusIfAvailable(inspectorReturnFocus));
      };
      auditedCloseInspector.__eqProofAudited = true;
      window.closeInspector = auditedCloseInspector;
    }
    inspectorClose?.addEventListener('click', () => {
      inspector.setAttribute('inert', '');
      queueMicrotask(() => focusIfAvailable(inspectorReturnFocus));
    });
  }

  const tour = document.getElementById('tourCard');
  const tourClose = document.getElementById('tourClose');
  let tourReturnFocus = null;
  if (tour) {
    const syncTourState = () => tour.setAttribute('aria-hidden', String(tour.hidden));
    new MutationObserver(syncTourState).observe(tour, { attributes: true, attributeFilter: ['hidden'] });
    syncTourState();
    ['guidedDemoButton', 'workspaceTourButton'].forEach((id) => {
      document.getElementById(id)?.addEventListener('click', (event) => {
        tourReturnFocus = event.currentTarget;
        requestAnimationFrame(() => {
          if (!tour.hidden) focusIfAvailable(tourClose);
        });
      });
    });
    if (typeof window.closeTour === 'function' && !window.closeTour.__eqProofAudited) {
      const originalCloseTour = window.closeTour;
      const auditedCloseTour = function closeAuditedTour(...args) {
        originalCloseTour(...args);
        queueMicrotask(() => focusIfAvailable(tourReturnFocus));
      };
      auditedCloseTour.__eqProofAudited = true;
      window.closeTour = auditedCloseTour;
    }
    tourClose?.addEventListener('click', () => queueMicrotask(() => focusIfAvailable(tourReturnFocus)));
  }

  document.addEventListener('keydown', (event) => {
    if (!tour?.hidden && isFormControl(event.target) && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.stopImmediatePropagation();
      return;
    }
    if (event.key === 'Escape' && inspector?.classList.contains('open') && tour?.hidden) {
      event.preventDefault();
      window.closeInspector?.();
    }
  }, true);

  const uploadDialog = document.getElementById('uploadDialog');
  const dialogClose = document.getElementById('dialogClose');
  let dialogReturnFocus = null;
  ['uploadButton', 'heroUploadButton'].forEach((id) => {
    document.getElementById(id)?.addEventListener('click', (event) => {
      dialogReturnFocus = event.currentTarget;
    });
  });
  dialogClose?.addEventListener('click', () => uploadDialog?.close('cancel'));
  uploadDialog?.addEventListener('close', () => focusIfAvailable(dialogReturnFocus));

  function synchronizeRuntimeCopy() {
    const addButton = document.getElementById('addEquationButton');
    const editorStatus = document.getElementById('editorStatus');
    if (!addButton) return;
    addButton.textContent = state.apiAvailable ? 'Validate and add' : 'Add to draft pack';
    if (!state.apiAvailable && editorStatus?.textContent.startsWith('Safe expression mode')) {
      editorStatus.textContent = 'Public draft mode performs structural checks only. Run the local app for authoritative engine validation.';
    }
  }

  if (typeof window.setRuntimeMode === 'function' && !window.setRuntimeMode.__eqProofAudited) {
    const originalSetRuntimeMode = window.setRuntimeMode;
    const auditedSetRuntimeMode = function setAuditedRuntimeMode(...args) {
      originalSetRuntimeMode(...args);
      synchronizeRuntimeCopy();
    };
    auditedSetRuntimeMode.__eqProofAudited = true;
    window.setRuntimeMode = auditedSetRuntimeMode;
  }
  synchronizeRuntimeCopy();

  window.downloadBlob = function downloadBlobSafely(content, type, filename) {
    const blob = new Blob([content], { type });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.download = filename;
    link.hidden = true;
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
})();
