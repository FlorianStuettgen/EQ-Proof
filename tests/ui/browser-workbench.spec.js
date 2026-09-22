const { test, expect } = require('@playwright/test');

async function loadWorkbench(page) {
  await page.goto('/');
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await expect(page.locator('#rememberWorkspaceInput')).toBeAttached();
  await expect(page.locator('#gateCard')).toHaveAttribute('aria-busy', 'false');
}

async function openWorkspaceOptions(page) {
  if (!await page.locator('#workspaceOptions').evaluate((element) => element.open)) {
    await page.locator('#workspaceOptions summary').click();
  }
}

async function compileCostFixture(page) {
  await page.locator('#uploadButton').click();
  await page.locator('#costInput').setInputFiles({
    name: 'browser-cost.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from([
      'control_account_id,AC,ETC,EAC,pending_change_exposure,risk_exposure,risk_adjusted_EAC',
      'TEST-1,10,5,12,2,1,15',
    ].join('\n')),
  });
  await page.locator('#compileButton').click();
  await expect(page.locator('#uploadDialog')).not.toBeVisible();
  await expect(page.locator('#workspaceTitle')).toHaveText('Browser-compiled monthly close');
}

test.beforeEach(async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.removeItem('eq-proof/browser-workspace@1');
    localStorage.removeItem('eq-proof/browser-persistence@1');
  });
});

test('hosted dialog accepts files and states the local-only boundary', async ({ page }) => {
  await loadWorkbench(page);
  await expect(page.locator('#rememberWorkspaceInput')).not.toBeChecked();
  await expect(page.locator('#browserWorkspaceStatus')).toContainText('Session only');
  await expect(page.locator('#uploadButton')).toHaveText('Analyze files');
  await page.locator('#uploadButton').click();
  await expect(page.locator('#uploadDialog')).toBeVisible();
  await expect(page.locator('#p6Input')).toBeEnabled();
  await expect(page.locator('#costInput')).toBeEnabled();
  await expect(page.locator('#compileButton')).toBeEnabled();
  await expect(page.locator('#apiStatus')).toContainText('Browser engine ready');
  await expect(page.locator('#uploadDescription')).toContainText('Nothing is uploaded');
  await expect(page.locator('#browserSampleInputs a')).toHaveCount(3);
  await expect(page.locator('#fileAnalysisPanel')).toBeVisible();
  await expect(page.locator('#showcaseCases')).toBeHidden();
});

test('compiles a cost file as session-only evidence by default', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadWorkbench(page);
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    window.__eqProofWorkspaceWrites = [];
    Storage.prototype.setItem = function recordedSetItem(key, value) {
      if (key === 'eq-proof/browser-workspace@1') window.__eqProofWorkspaceWrites.push(key);
      return original.call(this, key, value);
    };
  });
  await compileCostFixture(page);

  await expect(page.locator('#reportedEac')).toContainText('12');
  await expect(page.locator('#defensibleEac')).toContainText('15');
  await expect(page.locator('#deterministicGap')).toContainText('3');
  await expect(page.locator('#riskAdjustedPosition')).toContainText('18');
  await expect(page.locator('#sourceStrip')).toContainText('browser-cost.csv');
  await expect(page.locator('#apiStatus')).toContainText('session-only mode');

  const browserState = await page.evaluate(() => ({
    manifest: window.EQProofBrowser.getCurrentPayload().analysis.source_manifest,
    persisted: window.EQProofBrowser.getCurrentPayload().runtime.persisted_locally,
    stored: localStorage.getItem('eq-proof/browser-workspace@1'),
    workspaceWrites: window.__eqProofWorkspaceWrites,
  }));
  expect(browserState.manifest).toHaveLength(1);
  expect(browserState.manifest[0].sha256).toMatch(/^[a-f0-9]{64}$/);
  expect(browserState.manifest[0].records).toBe(1);
  expect(browserState.persisted).toBe(false);
  expect(browserState.stored).toBeNull();
  expect(browserState.workspaceWrites).toEqual([]);

  const [analysis] = await Promise.all([
    page.waitForEvent('download'),
    page.locator('#exportAnalysisButton').click(),
  ]);
  expect(analysis.suggestedFilename()).toBe('eq-proof-control-room.json');

  await page.reload();
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await expect(page.locator('#workspaceTitle')).not.toHaveText('Browser-compiled monthly close');
  await expect(page.locator('#reportedEac')).toContainText('407');
});

test('explicit persistence opt-in restores and can clear a workspace', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadWorkbench(page);
  await openWorkspaceOptions(page);
  await page.locator('#rememberWorkspaceInput').check();
  await compileCostFixture(page);

  const persisted = await page.evaluate(() => ({
    preference: localStorage.getItem('eq-proof/browser-persistence@1'),
    workspace: localStorage.getItem('eq-proof/browser-workspace@1'),
    flag: window.EQProofBrowser.getCurrentPayload().runtime.persisted_locally,
  }));
  expect(persisted.preference).toBe('enabled');
  expect(persisted.workspace).not.toBeNull();
  expect(persisted.flag).toBe(true);

  await page.reload();
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await expect(page.locator('#workspaceTitle')).toHaveText('Browser-compiled monthly close');
  await expect(page.locator('#reportedEac')).toContainText('12');
  await expect(page.locator('#rememberWorkspaceInput')).toBeChecked();

  await openWorkspaceOptions(page);
  await page.locator('#clearLocalWorkspaceButton').click();
  await expect(page.locator('#rememberWorkspaceInput')).not.toBeChecked();
  await expect(page.locator('#reportedEac')).toContainText('12');
  const cleared = await page.evaluate(() => ({
    preference: localStorage.getItem('eq-proof/browser-persistence@1'),
    workspace: localStorage.getItem('eq-proof/browser-workspace@1'),
  }));
  expect(cleared.preference).toBeNull();
  expect(cleared.workspace).toBeNull();
});

test('workspace options are keyboard accessible without crowding the result', async ({ page }) => {
  await loadWorkbench(page);
  await expect(page.locator('#exportAnalysisButton')).toBeVisible();
  await expect(page.locator('#rememberWorkspaceInput')).toBeHidden();
  await expect(page.locator('#openAnalysisButton')).toBeHidden();
  const toolbar = await page.locator('#browserWorkbenchBar').boundingBox();
  expect(toolbar.height).toBeLessThan(180);
  const summary = page.locator('#workspaceOptions summary');
  await summary.focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#rememberWorkspaceInput')).toBeVisible();
  await page.keyboard.press('Tab');
  await expect(page.locator('#rememberWorkspaceInput')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(summary).toBeFocused();
  await expect(page.locator('#rememberWorkspaceInput')).toBeHidden();
});

test('invalid analysis files preserve the active result and saved copy', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadWorkbench(page);
  await openWorkspaceOptions(page);
  await page.locator('#rememberWorkspaceInput').check();
  const before = await page.evaluate(() => ({
    payload: JSON.parse(JSON.stringify(EQProofBrowser.getCurrentPayload())),
    saved: localStorage.getItem('eq-proof/browser-workspace@1'),
    title: document.querySelector('#workspaceTitle').textContent,
  }));
  const partial = { schema_version: 'eq-proof/control-room@2', gate: { status: 'ready', label: 'CLOSE READY' }, analysis: {}, portfolio: { reported_eac: 1 } };
  const badRendering = JSON.parse(JSON.stringify(before.payload));
  badRendering.domain_summary = [{ domain: null }];
  for (const payload of [partial, badRendering]) {
    await page.locator('#openAnalysisInput').setInputFiles({ name: 'invalid-analysis.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(payload)) });
    await expect(page.locator('#browserWorkspaceStatus')).toContainText('current analysis was kept');
    await expect(page.locator('#workspaceTitle')).toHaveText(before.title);
    await expect(page.locator('#gateLabel')).toHaveText(before.payload.gate.label);
    expect(await page.evaluate(() => EQProofBrowser.getCurrentPayload())).toEqual(before.payload);
    expect(await page.evaluate(() => localStorage.getItem('eq-proof/browser-workspace@1'))).toBe(before.saved);
  }
});

test('a full browser store keeps the analysis session-only and explains recovery', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadWorkbench(page);
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function fullWorkspaceStorage(key, value) {
      if (key === 'eq-proof/browser-workspace@1') throw new DOMException('Quota exceeded', 'QuotaExceededError');
      return original.call(this, key, value);
    };
  });
  await openWorkspaceOptions(page);
  await page.locator('#rememberWorkspaceInput').click();
  await expect(page.locator('#browserWorkspaceStatus')).toContainText('could not save');
  await expect(page.locator('#rememberWorkspaceInput')).not.toBeChecked();
  expect(await page.evaluate(() => EQProofBrowser.getCurrentPayload().runtime.persisted_locally)).toBe(false);
  expect(await page.evaluate(() => localStorage.getItem('eq-proof/browser-workspace@1'))).toBeNull();
  await page.locator('#workspaceOptions summary').click();
  const [download] = await Promise.all([page.waitForEvent('download'), page.locator('#exportAnalysisButton').click()]);
  expect(download.suggestedFilename()).toBe('eq-proof-control-room.json');
});

test('restoring a synthetic example keeps its case identity', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name !== 'desktop');
  await loadWorkbench(page);
  await openWorkspaceOptions(page);
  await page.locator('#rememberWorkspaceInput').check();
  await page.locator('#workspaceOptions summary').click();
  await page.locator('#showcaseCasesButton').click();
  await page.locator('#showcaseCaseSelect').selectOption('ready');
  await page.locator('#runShowcaseCase').click();
  await expect(page.locator('#uploadDialog')).not.toBeVisible();
  await expect(page.locator('#workspaceTitle')).toContainText('Selected controls satisfied');
  const title = await page.locator('#workspaceTitle').textContent();
  expect(title).toContain('synthetic');
  await page.reload();
  await expect(page.locator('#browserWorkbenchBar')).toBeVisible();
  await expect(page.locator('#workspaceTitle')).toHaveText(title);
  await expect(page.locator('#browserWorkspaceStatus')).toContainText('Saved in this browser');
});

test('browser equation authoring validates and adds safe controls', async ({ page }) => {
  await loadWorkbench(page);
  await page.locator('#tab-equations').click();
  await expect(page.locator('#addEquationButton')).toHaveText('Validate in browser and add');

  await page.locator('#customExpression').fill('EAC <= delegated_authorization <= ceiling');
  await page.locator('#addEquationButton').click();
  await expect(page.locator('#editorStatus')).toContainText('exactly one comparison');

  await page.locator('#customExpression').fill('EAC <= delegated_authorization');
  await page.locator('#customFields').fill('EAC, delegated_authorization');
  await page.locator('#addEquationButton').click();
  await expect(page.locator('#editorStatus')).toContainText('validated by the browser engine');
  await expect(page.locator('.custom-chip')).toHaveCount(1);
});
